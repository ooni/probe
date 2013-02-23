import os
import sys
import time
import inspect
import traceback
import itertools
import random

import yaml

from twisted.python import reflect, usage
from twisted.internet import defer
from twisted.trial.runner import filenameToModule
from twisted.internet import reactor, threads

from txtorcon import TorProtocolFactory, TorConfig
from txtorcon import TorState, launch_tor

from ooni import config

from ooni.reporter import OONIBReporter, YAMLReporter, OONIBReportError

from ooni.inputunit import InputUnitFactory
from ooni.nettest import NetTestCase, NoPostProcessor

from ooni.utils import log, checkForRoot, pushFilenameStack
from ooni.utils import NotRootError, Storage
from ooni.utils.net import randomFreePort

def processTest(obj, cmd_line_options):
    """
    Process the parameters and :class:`twisted.python.usage.Options` of a
    :class:`ooni.nettest.Nettest`.

    :param obj:
        An uninstantiated old test, which should be a subclass of
        :class:`ooni.plugoo.tests.OONITest`.

    :param cmd_line_options:
        A configured and instantiated :class:`twisted.python.usage.Options`
        class.

    """
    if not hasattr(obj.usageOptions, 'optParameters'):
        obj.usageOptions.optParameters = []

    if obj.inputFile:
        obj.usageOptions.optParameters.append(obj.inputFile)

    if obj.baseParameters:
        for parameter in obj.baseParameters:
            obj.usageOptions.optParameters.append(parameter)

    if obj.baseFlags:
        if not hasattr(obj.usageOptions, 'optFlags'):
            obj.usageOptions.optFlags = []
        for flag in obj.baseFlags:
            obj.usageOptions.optFlags.append(flag)

    options = obj.usageOptions()

    options.parseOptions(cmd_line_options['subargs'])
    obj.localOptions = options

    if obj.inputFile:
        obj.inputFilename = options[obj.inputFile[0]]

    try:
        log.debug("processing options")
        tmp_test_case_object = obj()
        tmp_test_case_object._checkRequiredOptions()

    except usage.UsageError, e:
        test_name = tmp_test_case_object.name
        log.err("There was an error in running %s!" % test_name)
        log.err("%s" % e)
        options.opt_help()
        raise usage.UsageError("Error in parsing command line args for %s" % test_name)

    if obj.requiresRoot:
        try:
            checkForRoot()
        except NotRootError:
            log.err("%s requires root to run" % obj.name)
            sys.exit(1)

    return obj

def isTestCase(obj):
    try:
        return issubclass(obj, NetTestCase)
    except TypeError:
        return False

def findTestClassesFromFile(cmd_line_options):
    """
    Takes as input the command line config parameters and returns the test
    case classes.

    :param filename:
        the absolute path to the file containing the ooniprobe test classes

    :return:
        A list of class objects found in a file or module given on the
        commandline.
    """
    filename = cmd_line_options['test']
    classes = []
    module = filenameToModule(filename)
    for name, val in inspect.getmembers(module):
        if isTestCase(val):
            classes.append(processTest(val, cmd_line_options))
    return classes

def makeTestCases(klass, tests, method_prefix):
    """
    Takes a class some tests and returns the test cases. method_prefix is how
    the test case functions should be prefixed with.
    """
    cases = []
    for test in tests:
        cases.append((klass, method_prefix+test))
    return cases

class NoTestCasesFound(Exception):
    pass

def loadTestsAndOptions(classes, cmd_line_options):
    """
    Takes a list of test classes and returns their testcases and options.
    """
    method_prefix = 'test'
    options = None
    test_cases = []

    for klass in classes:
        tests = reflect.prefixedMethodNames(klass, method_prefix)
        if tests:
            test_cases = makeTestCases(klass, tests, method_prefix)

        test_klass = klass()
        options = test_klass._processOptions()

    if not test_cases:
        raise NoTestCasesFound

    return test_cases, options

def runTestCasesWithInput(test_cases, test_input, yaml_reporter,
        oonib_reporter=None):
    """
    Runs in parallel all the test methods that are inside of the specified test case.
    Reporting happens every time a Test Method has concluded running.
    Once all the test methods have been called we check to see if the
    postProcessing class method returns something. If it does return something
    we will write this as another entry inside of the report called post_processing.

    Args:

        test_cases (list): A list of tuples containing the test_class (a
            class) and the test_method (a string)

        test_input (instance): Any instance that will be passed as input to
            the test.

        yaml_reporter: An instance of :class:ooni.reporter.YAMLReporter

        oonib_reporter: An instance of :class:ooni.reporter.OONIBReporter. If
            this is set to none then we will only report to the YAML reporter.

    """

    # This is used to store a copy of all the test reports
    tests_report = {}

    def write_report(test_instance, test_name):
        if not oonib_reporter:
            return yaml_reporter.testDone(test_instance, test_name)
        d1 = oonib_reporter.testDone(test_instance, test_name)
        d2 = yaml_reporter.testDone(test_instance, test_name)
        dl = defer.DeferredList([d1, d2])
        @dl.addErrback
        def reportingFailed(failure):
            log.err("Error in reporting %s" % test_name)
            log.exception(failure)
        return dl

    def test_done(result, test_instance, test_name):
        log.msg("Finished running %s" % test_name)
        log.debug("Deferred callback result: %s" % result)
        tests_report[test_name] = dict(test_instance.report)
        return write_report(test_instance, test_name)

    def test_error(failure, test_instance, test_name):
        log.err("Error in running %s" % test_name)
        log.exception(failure)
        return write_report(test_instance, test_name)

    def tests_done(result, test_class):
        test_instance = test_class()
        test_instance.report = {}
        test_instance.input = None
        test_instance._start_time = time.time()
        post = getattr(test_instance, 'postProcessor')
        try:
            post_processing = post(tests_report)
            if not oonib_reporter:
                return yaml_reporter.testDone(test_instance, 'summary')
            d1 = oonib_reporter.testDone(test_instance, 'summary')
            d2 = yaml_reporter.testDone(test_instance, 'summary')
            return defer.DeferredList([d1, d2])
        except NoPostProcessor:
            log.debug("No post processor configured")
            return

    dl = []
    for test_case in test_cases:
        log.debug("Processing %s" % test_case[1])
        test_class = test_case[0]
        test_method = test_case[1]

        log.debug("Running %s with %s..." % (test_method, test_input))

        test_instance = test_class()
        test_instance.input = test_input
        test_instance.report = {}
        # use this to keep track of the test runtime
        test_instance._start_time = time.time()
        # call setups on the test
        test_instance._setUp()
        test_instance.setUp()
        test = getattr(test_instance, test_method)

        d = defer.maybeDeferred(test)
        d.addCallback(test_done, test_instance, test_method)
        d.addErrback(test_error, test_instance, test_method)
        dl.append(d)

    test_methods_d = defer.DeferredList(dl)
    test_methods_d.addCallback(tests_done, test_cases[0][0])
    @test_methods_d.addErrback
    def deferredListFailed(failure):
        log.err("Error Test Method Deferred List")
        log.exception(failure)

    return test_methods_d

def runTestCasesWithInputUnit(test_cases, input_unit, yaml_reporter,
        oonib_reporter):
    """
    Runs the Test Cases that are given as input parallely.
    A Test Case is a subclass of ooni.nettest.NetTestCase and a list of
    methods.

    The deferred list will fire once all the test methods have been
    run once per item in the input unit.

    test_cases: A list of tuples containing the test class and the test method as a string.

    input_unit: A generator that yields an input per iteration

    """
    log.debug("Running test cases with input unit")
    dl = []
    for test_input in input_unit:
        log.debug("Running test with this input %s" % test_input)
        d = runTestCasesWithInput(test_cases,
                test_input, yaml_reporter, oonib_reporter)
        dl.append(d)
    return defer.DeferredList(dl)

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

class UnableToStartTor(Exception):
    pass

def startTor():
    """ Starts Tor
    Launches a Tor with :param: socks_port :param: control_port
    :param: tor_binary set in ooniprobe.conf
    """
    @defer.inlineCallbacks
    def state_complete(state):
        config.tor_state = state
        log.msg("Successfully bootstrapped Tor")
        log.debug("We now have the following circuits: ")
        for circuit in state.circuits.values():
            log.debug(" * %s" % circuit)

        socks_port = yield state.protocol.get_conf("SocksPort")
        control_port = yield state.protocol.get_conf("ControlPort")
        client_ip = yield state.protocol.get_info("address")

        config.tor.socks_port = int(socks_port.values()[0])
        config.tor.control_port = int(control_port.values()[0])

        config.probe_ip = client_ip.values()[0]

        log.debug("Obtained our IP address from a Tor Relay %s" % config.privacy.client_ip)

    def setup_failed(failure):
        log.exception(failure)
        raise UnableToStartTor

    def setup_complete(proto):
        """
        Called when we read from stdout that Tor has reached 100%.
        """
        log.debug("Building a TorState")
        state = TorState(proto.tor_protocol)
        state.post_bootstrap.addCallback(state_complete)
        state.post_bootstrap.addErrback(setup_failed)
        return state.post_bootstrap

    def updates(prog, tag, summary):
        log.debug("%d%%: %s" % (prog, summary))

    tor_config = TorConfig()
    if config.tor.control_port:
        tor_config.ControlPort = config.tor.control_port
    else:
        control_port = int(randomFreePort())
        tor_config.ControlPort = control_port
        config.tor.control_port = control_port

    if config.tor.socks_port:
        tor_config.SocksPort = config.tor.socks_port
    else:
        socks_port = int(randomFreePort())
        tor_config.SocksPort = socks_port
        config.tor.socks_port = socks_port

    if config.tor.data_dir:
        data_dir = os.path.expanduser(config.tor.data_dir)

        if not os.path.exists(data_dir):
            log.msg("%s does not exist. Creating it." % data_dir)
            os.makedirs(data_dir)
        tor_config.DataDirectory = data_dir

    tor_config.save()

    log.debug("Setting control port as %s" % tor_config.ControlPort)
    log.debug("Setting SOCKS port as %s" % tor_config.SocksPort)

    d = launch_tor(tor_config, reactor,
            tor_binary=config.advanced.tor_binary,
            progress_updates=updates)
    d.addCallback(setup_complete)
    d.addErrback(setup_failed)
    return d

def startSniffing():
    """ Start sniffing with Scapy. Exits if required privileges (root) are not
    available.
    """
    from ooni.utils.txscapy import ScapyFactory, ScapySniffer
    try:
        checkForRoot()
    except NotRootError:
        print "[!] Includepcap options requires root priviledges to run"
        print "    you should run ooniprobe as root or disable the options in ooniprobe.conf"
        sys.exit(1)

    print "Starting sniffer"
    config.scapyFactory = ScapyFactory(config.advanced.interface)

    if os.path.exists(config.reports.pcap):
        print "Report PCAP already exists with filename %s" % config.reports.pcap
        print "Renaming files with such name..."
        pushFilenameStack(config.reports.pcap)

    sniffer = ScapySniffer(config.reports.pcap)
    config.scapyFactory.registerProtocol(sniffer)

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
