import os
import re
import time

from twisted.internet import defer, reactor
from twisted.trial.runner import filenameToModule
from twisted.python import usage, reflect

from ooni import geoip
from ooni.tasks import Measurement
from ooni.utils import log, checkForRoot
from ooni import otime
from ooni.settings import config

from ooni import errors as e

from inspect import getmembers
from StringIO import StringIO

class NoTestCasesFound(Exception):
    pass

def get_test_methods(item, method_prefix="test_"):
    """
    Look for test_ methods in subclasses of NetTestCase
    """
    test_cases = []
    try:
        assert issubclass(item, NetTestCase)
        methods = reflect.prefixedMethodNames(item, method_prefix)
        test_methods = []
        for method in methods:
            test_methods.append(method_prefix + method)
        if test_methods:
            test_cases.append((item, test_methods))
    except (TypeError, AssertionError):
        pass
    return test_cases

def loadNetTestString(net_test_string):
    """
    Load NetTest from a string.
    WARNING input to this function *MUST* be sanitized and *NEVER* be
    untrusted.
    Failure to do so will result in code exec.

    net_test_string:

        a string that contains the net test to be run.
    """
    net_test_file_object = StringIO(net_test_string)

    ns = {}
    test_cases = []
    exec net_test_file_object.read() in ns
    for item in ns.itervalues():
        test_cases.extend(get_test_methods(item))

    if not test_cases:
        raise NoTestCasesFound

    return test_cases

def loadNetTestFile(net_test_file):
    """
    Load NetTest from a file.
    """
    test_cases = []
    module = filenameToModule(net_test_file)
    for __, item in getmembers(module):
        test_cases.extend(get_test_methods(item))

    if not test_cases:
        raise NoTestCasesFound

    return test_cases

def getTestClassFromFile(net_test_file):
    """
    Will return the first class that is an instance of NetTestCase.

    XXX this means that if inside of a test there are more than 1 test case
        then we will only run the first one.
    """
    module = filenameToModule(net_test_file)
    for __, item in getmembers(module):
        try:
            assert issubclass(item, NetTestCase)
            return item
        except (TypeError, AssertionError):
            pass

def getOption(opt_parameter, required_options, type='text'):
    """
    Arguments:
        usage_options: a list as should be the optParameters of an UsageOptions class.

        required_options: a list containing the strings of the options that are
            required.

        type: a string containing the type of the option.

    Returns:
        a dict containing
            {
                'description': the description of the option,
                'default': the default value of the option,
                'required': True|False if the option is required or not,
                'type': the type of the option ('text' or 'file')
            }
    """
    option_name, _, default, description = opt_parameter
    if option_name in required_options:
        required = True
    else:
        required = False

    return {'description': description,
        'value': default, 'required': required,
        'type': type
    }

def getArguments(test_class):
    arguments = {}
    if test_class.inputFile:
        option_name = test_class.inputFile[0]
        arguments[option_name] = getOption(test_class.inputFile,
                test_class.requiredOptions, type='file')
    try:
        list(test_class.usageOptions.optParameters)
    except AttributeError:
        return arguments

    for opt_parameter in test_class.usageOptions.optParameters:
        option_name = opt_parameter[0]
        opt_type="text"
        if opt_parameter[3].lower().startswith("file"):
            opt_type="file"
        arguments[option_name] = getOption(opt_parameter,
                test_class.requiredOptions, type=opt_type)

    return arguments

def test_class_name_to_name(test_class_name):
    return test_class_name.lower().replace(' ','_')

def getNetTestInformation(net_test_file):
    """
    Returns a dict containing:

    {
        'id': the test filename excluding the .py extension,
        'name': the full name of the test,
        'description': the description of the test,
        'version': version number of this test,
        'arguments': a dict containing as keys the supported arguments and as
            values the argument description.
    }
    """
    test_class = getTestClassFromFile(net_test_file)

    test_id = test_class_name_to_name(test_class.name)
    information = {'id': test_id,
        'name': test_class.name,
        'description': test_class.description,
        'version': test_class.version,
        'arguments': getArguments(test_class),
        'path': net_test_file
    }
    return information

class NetTestLoader(object):
    method_prefix = 'test'

    def __init__(self, options, test_file=None, test_string=None):
        self.options = options
        test_cases = None

        if test_file:
            test_cases = loadNetTestFile(test_file)
        elif test_string:
            test_cases = loadNetTestString(test_string)

        if test_cases:
            self.setupTestCases(test_cases)

    @property
    def testDetails(self):
        from ooni import __version__ as software_version

        client_geodata = {}
        if config.probe_ip.address and (config.privacy.includeip or \
                config.privacy.includeasn or \
                config.privacy.includecountry or \
                config.privacy.includecity):
            log.msg("We will include some geo data in the report")
            try:
                client_geodata = geoip.IPToLocation(config.probe_ip.address)
            except e.GeoIPDataFilesNotFound:
                log.err("Unable to find the geoip data files")
                client_geodata = {'city': None, 'countrycode': None, 'asn': None}

        if config.privacy.includeip:
            client_geodata['ip'] = config.probe_ip.address
        else:
            client_geodata['ip'] = "127.0.0.1"

        # Here we unset all the client geodata if the option to not include then
        # has been specified
        if client_geodata and not config.privacy.includeasn:
            client_geodata['asn'] = 'AS0'
        elif 'asn' in client_geodata:
            # XXX this regexp should probably go inside of geodata
            client_geodata['asn'] = client_geodata['asn']
            log.msg("Your AS number is: %s" % client_geodata['asn'])
        else:
            client_geodata['asn'] = None

        if (client_geodata and not config.privacy.includecity) \
                or ('city' not in client_geodata):
            client_geodata['city'] = None

        if (client_geodata and not config.privacy.includecountry) \
                or ('countrycode' not in client_geodata):
            client_geodata['countrycode'] = None

        test_details = {'start_time': time.time(),
            'probe_asn': client_geodata['asn'],
            'probe_cc': client_geodata['countrycode'],
            'probe_ip': client_geodata['ip'],
            'test_name': self.testName,
            'test_version': self.testVersion,
            'software_name': 'ooniprobe',
            'software_version': software_version,
            'options': self.options
        }
        return test_details


    def _parseNetTestOptions(self, klass):
        """
        Helper method to assemble the options into a single UsageOptions object
        """
        usage_options = klass.usageOptions

        if not hasattr(usage_options, 'optParameters'):
            usage_options.optParameters = []
        else:
            for parameter in usage_options.optParameters:
                if len(parameter) == 5:
                    parameter.pop()

        if klass.inputFile:
            usage_options.optParameters.append(klass.inputFile)

        if klass.baseParameters:
            for parameter in klass.baseParameters:
                usage_options.optParameters.append(parameter)

        if klass.baseFlags:
            if not hasattr(usage_options, 'optFlags'):
                usage_options.optFlags = []
            for flag in klass.baseFlags:
                usage_options.optFlags.append(flag)

        return usage_options

    @property
    def usageOptions(self):
        usage_options = None
        for test_class, test_method in self.testCases:
            if not usage_options:
                usage_options = self._parseNetTestOptions(test_class)
            else:
                assert usage_options == test_class.usageOptions
        return usage_options

    def loadNetTestString(self, net_test_string):
        """
        Load NetTest from a string.
        WARNING input to this function *MUST* be sanitized and *NEVER* take
        untrusted input.
        Failure to do so will result in code exec.

        net_test_string:

            a string that contains the net test to be run.
        """
        net_test_file_object = StringIO(net_test_string)

        ns = {}
        test_cases = []
        exec net_test_file_object.read() in ns
        for item in ns.itervalues():
            test_cases.extend(self._get_test_methods(item))

        if not test_cases:
            raise NoTestCasesFound

        self.setupTestCases(test_cases)

    def loadNetTestFile(self, net_test_file):
        """
        Load NetTest from a file.
        """
        test_cases = []
        module = filenameToModule(net_test_file)
        for __, item in getmembers(module):
            test_cases.extend(self._get_test_methods(item))

        if not test_cases:
            raise NoTestCasesFound

        self.setupTestCases(test_cases)

    def setupTestCases(self, test_cases):
        """
        Creates all the necessary test_cases (a list of tuples containing the
        NetTestCase (test_class, test_method))

        example:
            [(test_classA, test_method1),
            (test_classA, test_method2),
            (test_classA, test_method3),
            (test_classA, test_method4),
            (test_classA, test_method5),

            (test_classB, test_method1),
            (test_classB, test_method2)]

        Note: the inputs must be valid for test_classA and test_classB.

        net_test_file:
            is either a file path or a file like object that will be used to
            generate the test_cases.
        """
        test_class, _ = test_cases[0]
        self.testVersion = test_class.version
        self.testName = test_class_name_to_name(test_class.name)
        self.testCases = test_cases

    def checkOptions(self):
        """
        Call processTest and processOptions methods of each NetTestCase
        """
        test_classes = set([])
        for test_class, test_method in self.testCases:
            test_classes.add(test_class)

        for klass in test_classes:
            options = self.usageOptions()
            options.parseOptions(self.options)

            if options:
                klass.localOptions = options

            test_instance = klass()
            if test_instance.requiresRoot:
                checkForRoot()
            test_instance._checkRequiredOptions()
            test_instance._checkValidOptions()

            inputs = test_instance.getInputProcessor()
            if not inputs:
                inputs = [None]
            klass.inputs = inputs

    def _get_test_methods(self, item):
        """
        Look for test_ methods in subclasses of NetTestCase
        """
        test_cases = []
        try:
            assert issubclass(item, NetTestCase)
            methods = reflect.prefixedMethodNames(item, self.method_prefix)
            test_methods = []
            for method in methods:
                test_methods.append(self.method_prefix + method)
            if test_methods:
                test_cases.append((item, test_methods))
        except (TypeError, AssertionError):
            pass
        return test_cases

class NetTestState(object):
    def __init__(self, allTasksDone):
        """
        This keeps track of the state of a running NetTests case.

        Args:
            allTasksDone is a deferred that will get fired once all the NetTest
            cases have reached a final done state.
        """
        self.doneTasks = 0
        self.tasks = 0

        self.completedScheduling = False
        self.allTasksDone = allTasksDone

    def taskCreated(self):
        self.tasks += 1

    def checkAllTasksDone(self):
        log.debug("Checking all tasks for completion %s == %s" %
                  (self.doneTasks, self.tasks))
        if self.completedScheduling and \
                self.doneTasks == self.tasks:
            self.allTasksDone.callback(self.doneTasks)

    def taskDone(self):
        """
        This is called every time a task has finished running.
        """
        self.doneTasks += 1
        self.checkAllTasksDone()

    def allTasksScheduled(self):
        """
        This should be called once all the tasks that need to run have been
        scheduled.

        XXX this is ghetto.
        The reason for which we are calling allTasksDone inside of the
        allTasksScheduled method is called after all tasks are done, then we
        will run into a race condition. The race is that we don't end up
        checking that all the tasks are complete because no task is to be
        scheduled.
        """
        self.completedScheduling = True
        self.checkAllTasksDone()

class NetTest(object):
    director = None

    def __init__(self, net_test_loader, report):
        """
        net_test_loader:
             an instance of :class:ooni.nettest.NetTestLoader containing
             the test to be run.
        """
        self.report = report
        self.testCases = net_test_loader.testCases

        # This will fire when all the measurements have been completed and
        # all the reports are done. Done means that they have either completed
        # successfully or all the possible retries have been reached.
        self.done = defer.Deferred()

        self.state = NetTestState(self.done)

    def doneReport(self, report_results):
        """
        This will get called every time a report is done and therefore a
        measurement is done.

        The state for the NetTest is informed of the fact that another task has
        reached the done state.
        """
        self.state.taskDone()

        if len(self.report.reporters) == 0:
            raise e.AllReportersFailed

        return report_results

    def makeMeasurement(self, test_class, test_method, test_input=None):
        """
        Creates a new instance of :class:ooni.tasks.Measurement and add's it's
        callbacks and errbacks.

        Args:
            test_class:
                a subclass of :class:ooni.nettest.NetTestCase

            test_method:
                a string that represents the method to be called on test_class

            test_input:
                optional argument that represents the input to be passed to the
                NetTestCase

        """
        measurement = Measurement(test_class, test_method, test_input)
        measurement.netTest = self

        if self.director:
            measurement.done.addCallback(self.director.measurementSucceeded)
            measurement.done.addErrback(self.director.measurementFailed,
                                        measurement)

        if self.report:
            measurement.done.addBoth(self.report.write)

        if self.report and self.director:
            measurement.done.addBoth(self.doneReport)

        return measurement

    def generateMeasurements(self):
        """
        This is a generator that yields measurements and registers the
        callbacks for when a measurement is successful or has failed.
        """
        for test_class, test_methods in self.testCases:
            for input in test_class.inputs:
                for method in test_methods:
                    log.debug("Running %s %s" % (test_class, method))
                    measurement = self.makeMeasurement(test_class, method, input)
                    self.state.taskCreated()
                    yield measurement

        self.state.allTasksScheduled()

class NetTestCase(object):
    """
    This is the base of the OONI nettest universe. When you write a nettest
    you will subclass this object.

    * inputs: can be set to a static set of inputs. All the tests (the methods
      starting with the "test" prefix) will be run once per input.  At every run
      the _input_ attribute of the TestCase instance will be set to the value of
      the current iteration over inputs.  Any python iterable object can be set
      to inputs.

    * inputFile: attribute should be set to an array containing the command line
      argument that should be used as the input file. Such array looks like
      this:

          ``["commandlinearg", "c", "default value" "The description"]``

      The second value of such arrray is the shorthand for the command line arg.
      The user will then be able to specify inputs to the test via:

          ``ooniprobe mytest.py --commandlinearg path/to/file.txt``

      or

          ``ooniprobe mytest.py -c path/to/file.txt``


    * inputProcessor: should be set to a function that takes as argument a
      filename and it will return the input to be passed to the test
      instance.

    * name: should be set to the name of the test.

    * author: should contain the name and contact details for the test author.
      The format for such string is as follows:

          ``The Name <email@example.com>``

    * version: is the version string of the test.

    * requiresRoot: set to True if the test must be run as root.

    * usageOptions: a subclass of twisted.python.usage.Options for processing of command line arguments

    * localOptions: contains the parsed command line arguments.

    Quirks:
    Every class that is prefixed with test *must* return a twisted.internet.defer.Deferred.
    """
    name = "This test is nameless"
    author = "Jane Doe <foo@example.com>"
    version = "0.0.0"
    description = "Sorry, this test has no description :("

    inputs = [None]
    inputFile = None
    inputFilename = None

    report = {}
    report['errors'] = []

    usageOptions = usage.Options

    optParameters = None
    baseParameters = None
    baseFlags = None

    requiredOptions = []
    requiresRoot = False

    localOptions = {}
    def _setUp(self):
        """
        This is the internal setup method to be overwritten by templates.
        """
        pass

    def setUp(self):
        """
        Place here your logic to be executed when the test is being setup.
        """
        pass

    def postProcessor(self, report):
        """
        Subclass this to do post processing tasks that are to occur once all
        the test methods have been called. Once per input.
        postProcessing works exactly like test methods, in the sense that
        anything that gets written to the object self.report[] will be added to
        the final test report.
        """
        raise NoPostProcessor

    def inputProcessor(self, filename):
        """
        You may replace this with your own custom input processor. It takes as
        input a file name.

        An inputProcessor is an iterator that will yield one item from the file
        and takes as argument a filename.

        This can be useful when you have some input data that is in a certain
        format and you want to set the input attribute of the test to something
        that you will be able to properly process.

        For example you may wish to have an input processor that will allow you
        to ignore comments in files. This can be easily achieved like so::

            fp = open(filename)
            for x in fp.xreadlines():
                if x.startswith("#"):
                    continue
                yield x.strip()
            fp.close()

        Other fun stuff is also possible.
        """
        log.debug("Running default input processor")
        with open(filename) as f:
            for line in f:
                yield line.strip()

    @property
    def inputFileSpecified(self):
        """
        Returns:
            True
                when inputFile is supported and is specified
            False
                when input is either not support or not specified
        """
        if not self.inputFile:
            return False

        k = self.inputFile[0]
        if self.localOptions.get(k):
            return True
        else:
            return False

    def getInputProcessor(self):
        """
        This method must be called after all options are validated by
        _checkValidOptions and _checkRequiredOptions, which ensure that
        if the inputFile is a required option it will be present.

        We check to see if it's possible to have an input file and if the user
        has specified such file.

        Returns:
            a generator that will yield one item from the file based on the
            inputProcessor.
        """
        if self.inputFileSpecified:
            self.inputFilename = self.localOptions[self.inputFile[0]]
            return self.inputProcessor(self.inputFilename)

        return None

    def _checkValidOptions(self):
        for option in self.localOptions:
            if option not in self.usageOptions():
                if not self.inputFile or option not in self.inputFile:
                    raise InvalidOption

    def _checkRequiredOptions(self):
        for required_option in self.requiredOptions:
            log.debug("Checking if %s is present" % required_option)
            if required_option not in self.localOptions or \
                self.localOptions[required_option] == None:
                raise MissingRequiredOption(required_option)

    def __repr__(self):
        return "<%s inputs=%s>" % (self.__class__, self.inputs)

class FailureToLoadNetTest(Exception):
    pass
class NoPostProcessor(Exception):
    pass
class InvalidOption(Exception):
    pass
class MissingRequiredOption(Exception):
    pass
