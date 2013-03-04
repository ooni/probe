import os
import time
import random

import yaml

from twisted.internet import defer
from twisted.internet import reactor

from txtorcon import TorConfig
from txtorcon import TorState, launch_tor

from ooni import config
from ooni.reporter import OONIBReporter, YAMLReporter, OONIBReportError
from ooni.inputunit import InputUnitFactory
from ooni.nettest import NetTestCase, NoPostProcessor
from ooni.utils import log, checkForRoot, pushFilenameStack
from ooni.utils import NotRootError, Storage
from ooni.utils.net import randomFreePort

class InvalidResumeFile(Exception):
    pass

class noResumeSession(Exception):
    pass

def loadResumeFile():
    """
    Sets the singleton stateDict object to the content of the resume file.
    If the file is empty then it will create an empty one.

    Raises:

        :class:ooni.runner.InvalidResumeFile if the resume file is not valid

    """
    if not config.stateDict:
        try:
            with open(config.resume_filename) as f:
                config.stateDict = yaml.safe_load(f)
        except:
            log.err("Error loading YAML file")
            raise InvalidResumeFile

        if not config.stateDict:
            with open(config.resume_filename, 'w+') as f:
                yaml.safe_dump(dict(), f)
            config.stateDict = dict()

        elif isinstance(config.stateDict, dict):
            return
        else:
            log.err("The resume file is of the wrong format")
            raise InvalidResumeFile

def resumeTest(test_filename, input_unit_factory):
    """
    Returns the an input_unit_factory that is at the index of the previous run of the test 
    for the specified test_filename.

    Args:

        test_filename (str): the filename of the test that is being run
            including the .py extension.

        input_unit_factory (:class:ooni.inputunit.InputUnitFactory): with the
            same input of the past run.

    Returns:

        :class:ooni.inputunit.InputUnitFactory that is at the index of the
            previous test run.

    """
    try:
        idx = config.stateDict[test_filename]
        for x in range(idx):
            try:
                input_unit_factory.next()
            except StopIteration:
                log.msg("Previous run was complete")
                return input_unit_factory

        return input_unit_factory

    except KeyError:
        log.debug("No resume key found for selected test name. It is therefore 0")
        config.stateDict[test_filename] = 0
        return input_unit_factory

@defer.inlineCallbacks
def updateResumeFile(test_filename):
    """
    update the resume file with the current stateDict state.
    """
    log.debug("Acquiring lock for %s" % test_filename)
    yield config.resume_lock.acquire()

    current_resume_state = yaml.safe_load(open(config.resume_filename))
    current_resume_state = config.stateDict
    yaml.safe_dump(current_resume_state, open(config.resume_filename, 'w+'))

    log.debug("Releasing lock for %s" % test_filename)
    config.resume_lock.release()
    defer.returnValue(config.stateDict[test_filename])

@defer.inlineCallbacks
def increaseInputUnitIdx(test_filename):
    """
    Args:

        test_filename (str): the filename of the test that is being run
            including the .py extension.

        input_unit_idx (int): the current input unit index for the test.

    """
    config.stateDict[test_filename] += 1
    yield updateResumeFile(test_filename)

def updateProgressMeters(test_filename, input_unit_factory, 
        test_case_number):
    """
    Update the progress meters for keeping track of test state.
    """
    if not config.state.test_filename:
        config.state[test_filename] = Storage()

    config.state[test_filename].per_item_average = 2.0

    input_unit_idx = float(config.stateDict[test_filename])
    input_unit_items = len(input_unit_factory)
    test_case_number = float(test_case_number)
    total_iterations = input_unit_items * test_case_number
    current_iteration = input_unit_idx * test_case_number

    log.debug("input_unit_items: %s" % input_unit_items)
    log.debug("test_case_number: %s" % test_case_number)

    log.debug("Test case number: %s" % test_case_number)
    log.debug("Total iterations: %s" % total_iterations)
    log.debug("Current iteration: %s" % current_iteration)

    def progress():
        return (current_iteration / total_iterations) * 100.0

    config.state[test_filename].progress = progress

    def eta():
        return (total_iterations - current_iteration) \
                * config.state[test_filename].per_item_average
    config.state[test_filename].eta = eta

    config.state[test_filename].input_unit_idx = input_unit_idx
    config.state[test_filename].input_unit_items = input_unit_items


@defer.inlineCallbacks
def runTestCases(test_cases, options, cmd_line_options):
    log.debug("Running %s" % test_cases)
    log.debug("Options %s" % options)
    log.debug("cmd_line_options %s" % dict(cmd_line_options))

    test_inputs = options['inputs']

    # Set a default reporter
    if not cmd_line_options['collector'] and not \
        cmd_line_options['no-default-reporter']:
        with open('collector') as f:
            reporter_url = random.choice(f.readlines())
            reporter_url = reporter_url.split('#')[0].strip()
            cmd_line_options['collector'] = reporter_url

    oonib_reporter = OONIBReporter(cmd_line_options)
    yaml_reporter = YAMLReporter(cmd_line_options)

    if cmd_line_options['collector']:
        log.msg("Using remote collector, please be patient while we create the report.")
        try:
            yield oonib_reporter.createReport(options)
        except OONIBReportError:
            log.err("Error in creating new report")
            log.msg("We will only create reports to a file")
            oonib_reporter = None
    else:
        oonib_reporter = None

    yield yaml_reporter.createReport(options)
    log.msg("Reporting to file %s" % yaml_reporter._stream.name)

    try:
        input_unit_factory = InputUnitFactory(test_inputs)
        input_unit_factory.inputUnitSize = int(cmd_line_options['parallelism'])
    except Exception, e:
        log.exception(e)

    try:
        loadResumeFile()
    except InvalidResumeFile:
        log.err("Error in loading resume file %s" % config.resume_filename)
        log.err("Try deleting the resume file")
        raise InvalidResumeFile

    test_filename = os.path.basename(cmd_line_options['test'])

    if cmd_line_options['resume']:
        log.debug("Resuming %s" % test_filename)
        resumeTest(test_filename, input_unit_factory)
    else:
        log.debug("Not going to resume %s" % test_filename)
        config.stateDict[test_filename] = 0

    updateProgressMeters(test_filename, input_unit_factory, len(test_cases))

    try:
        for input_unit in input_unit_factory:
            log.debug("Running %s with input unit %s" % (test_filename, input_unit))

            yield runTestCasesWithInputUnit(test_cases, input_unit,
                    yaml_reporter, oonib_reporter)

            yield increaseInputUnitIdx(test_filename)

            updateProgressMeters(test_filename, input_unit_factory, len(test_cases))

    except Exception:
        log.exception("Problem in running test")
    yaml_reporter.finish()

def loadTest(cmd_line_options):
    """
    Takes care of parsing test command line arguments and loading their
    options.
    """
    # XXX here there is too much strong coupling with cmd_line_options
    # Ideally this would get all wrapped in a nice little class that get's
    # instanced with it's cmd_line_options as an instance attribute
    classes = findTestClassesFromFile(cmd_line_options)
    test_cases, options = loadTestsAndOptions(classes, cmd_line_options)

    return test_cases, options, cmd_line_options
