import os
import re

from twisted.internet import defer, reactor
from twisted.trial.runner import filenameToModule
from twisted.python import usage, reflect

from ooni.tasks import Measurement
from ooni.utils import log, checkForRoot, NotRootError, geodata
from ooni import config
from ooni import otime

from ooni.errors import AllReportersFailed

from inspect import getmembers
from StringIO import StringIO

class NoTestCasesFound(Exception):
    pass

class NetTestLoader(object):
    method_prefix = 'test'

    def __init__(self, options):
        self.options = options
        self.testCases = self.loadNetTest(options['test'])

    @property
    def testDetails(self):
        from ooni import __version__ as software_version

        client_geodata = {}
        if config.probe_ip and (config.privacy.includeip or \
                config.privacy.includeasn or \
                config.privacy.includecountry or \
                config.privacy.includecity):
            log.msg("We will include some geo data in the report")
            client_geodata = geodata.IPToLocation(config.probe_ip)

        if config.privacy.includeip:
            client_geodata['ip'] = config.probe_ip
        else:
            client_geodata['ip'] = "127.0.0.1"

        # Here we unset all the client geodata if the option to not include then
        # has been specified
        if client_geodata and not config.privacy.includeasn:
            client_geodata['asn'] = 'AS0'
        elif 'asn' in client_geodata:
            # XXX this regexp should probably go inside of geodata
            client_geodata['asn'] = \
                    re.search('AS\d+', client_geodata['asn']).group(0)
            log.msg("Your AS number is: %s" % client_geodata['asn'])
        else:
            client_geodata['asn'] = None

        if (client_geodata and not config.privacy.includecity) \
                or ('city' not in client_geodata):
            client_geodata['city'] = None

        if (client_geodata and not config.privacy.includecountry) \
                or ('countrycode' not in client_geodata):
            client_geodata['countrycode'] = None

        test_details = {'start_time': otime.utcTimeNow(),
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

    def loadNetTest(self, net_test_file):
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
        test_cases = None
        try:
            if os.path.isfile(net_test_file):
                test_cases = self._loadNetTestFile(net_test_file)
            else:
                net_test_file = StringIO(net_test_file)
                raise TypeError("not a file path")

        except TypeError:
            if hasattr(net_test_file, 'read'):
                test_cases = self._loadNetTestFromFileObject(net_test_file)

        if not test_cases:
            raise NoTestCasesFound

        test_class, _ = test_cases[0]
        self.testVersion = test_class.version
        self.testName = test_class.name.lower().replace(' ','_')
        return test_cases

    def checkOptions(self):
        """
        Call processTest and processOptions methods of each NetTestCase
        """
        test_classes = set([])
        for test_class, test_method in self.testCases:
            test_classes.add(test_class)

        for klass in test_classes:
            options = self.usageOptions()
            options.parseOptions(self.options['subargs'])
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

    def _loadNetTestFromFileObject(self, net_test_string):
        """
        Load NetTest from a string
        """
        ns = {}
        test_cases = []
        exec net_test_string.read() in ns
        for item in ns.itervalues():
            test_cases.extend(self._get_test_methods(item))
        return test_cases

    def _loadNetTestFile(self, net_test_file):
        """
        Load NetTest from a file
        """
        test_cases = []
        module = filenameToModule(net_test_file)
        for __, item in getmembers(module):
            test_cases.extend(self._get_test_methods(item))
        return test_cases

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

        Args:
            report_results:
                is the list of tuples returned by the self.report.write
                :class:twisted.internet.defer.DeferredList

        Returns:
            the same deferred list results
        """
        for report_status, report_result in report_results:
            if report_status == False:
                self.director.reporterFailed(report_result, self)

        self.state.taskDone()

        if len(self.report.reporters) == 0:
            raise AllReportersFailed

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
            measurement.done.addErrback(self.director.measurementFailed, measurement)

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
    name = "I Did Not Change The Name"
    author = "Jane Doe <foo@example.com>"
    version = "0.0.0"

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
