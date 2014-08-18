import os
import re
import time
import sys
from hashlib import sha256

from twisted.internet import defer
from twisted.trial.runner import filenameToModule
from twisted.python import usage, reflect

from ooni.tasks import Measurement
from ooni.utils import log, checkForRoot, sanitize_options
from ooni.settings import config

from ooni import errors as e

from inspect import getmembers
from StringIO import StringIO


class NoTestCasesFound(Exception):
    pass


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
        usage_options: a list as should be the optParameters of an UsageOptions
            class.

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
        arguments[option_name] = getOption(
            test_class.inputFile,
            test_class.requiredOptions,
            type='file')
    try:
        list(test_class.usageOptions.optParameters)
    except AttributeError:
        return arguments

    for opt_parameter in test_class.usageOptions.optParameters:
        option_name = opt_parameter[0]
        opt_type = "text"
        if opt_parameter[3].lower().startswith("file"):
            opt_type = "file"
        arguments[option_name] = getOption(
            opt_parameter,
            test_class.requiredOptions,
            type=opt_type)

    return arguments


def test_class_name_to_name(test_class_name):
    return test_class_name.lower().replace(' ', '_')


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

    test_id = os.path.basename(net_test_file).replace('.py', '')
    information = {'id': test_id,
                   'name': test_class.name,
                   'description': test_class.description,
                   'version': test_class.version,
                   'arguments': getArguments(test_class),
                   'path': net_test_file,
                   }
    return information


class NetTestLoader(object):
    method_prefix = 'test'
    collector = None
    requiresTor = False

    def __init__(self, options, test_file=None, test_string=None):
        self.onionInputRegex = re.compile(
            "(httpo://[a-z0-9]{16}\.onion)/input/([a-z0-9]{64})$")
        self.options = options
        self.testCases = []

        if test_file:
            self.loadNetTestFile(test_file)
        elif test_string:
            self.loadNetTestString(test_string)

    @property
    def requiredTestHelpers(self):
        required_test_helpers = []
        if not self.testCases:
            return required_test_helpers

        for test_class, test_methods in self.testCases:
            for option, name in test_class.requiredTestHelpers.items():
                required_test_helpers.append({
                    'name': name,
                    'option': option,
                    'test_class': test_class
                })
        return required_test_helpers

    @property
    def inputFiles(self):
        input_files = []
        if not self.testCases:
            return input_files

        for test_class, test_methods in self.testCases:
            if test_class.inputFile:
                key = test_class.inputFile[0]
                filename = test_class.localOptions[key]
                if not filename:
                    continue
                input_file = {
                    'key': key,
                    'test_class': test_class
                }
                m = self.onionInputRegex.match(filename)
                if m:
                    input_file['url'] = filename
                    input_file['address'] = m.group(1)
                    input_file['hash'] = m.group(2)
                else:
                    input_file['filename'] = filename
                    try:
                        with open(filename) as f:
                            h = sha256()
                            for l in f:
                                h.update(l)
                    except:
                        raise e.InvalidInputFile(filename)
                    input_file['hash'] = h.hexdigest()
                input_files.append(input_file)

        return input_files

    @property
    def testDetails(self):
        from ooni import __version__ as software_version

        input_file_hashes = []
        for input_file in self.inputFiles:
            input_file_hashes.append(input_file['hash'])

        options = sanitize_options(self.options)
        test_details = {'start_time': time.time(),
                        'probe_asn': config.probe_ip.geodata['asn'],
                        'probe_cc': config.probe_ip.geodata['countrycode'],
                        'probe_ip': config.probe_ip.geodata['ip'],
                        'probe_city': config.probe_ip.geodata['city'],
                        'test_name': self.testName,
                        'test_version': self.testVersion,
                        'software_name': 'ooniprobe',
                        'software_version': software_version,
                        'options': options,
                        'input_hashes': input_file_hashes
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
            raise e.NoTestCasesFound

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
            raise e.NoTestCasesFound

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
        self.testClasses = set([])
        for test_class, test_method in self.testCases:
            self.testClasses.add(test_class)

    def checkOptions(self):
        """
        Call processTest and processOptions methods of each NetTestCase
        """
        for klass in self.testClasses:
            options = self.usageOptions()
            try:
                options.parseOptions(self.options)
            except usage.UsageError:
                tb = sys.exc_info()[2]
                raise e.OONIUsageError(self), None, tb

            if options:
                klass.localOptions = options

            test_instance = klass()
            if test_instance.requiresRoot:
                checkForRoot()
            if test_instance.requiresTor:
                self.requiresTor = True
            test_instance.requirements()
            test_instance._checkRequiredOptions()
            test_instance._checkValidOptions()

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

        report:
            an instance of :class:ooni.reporter.Reporter
        """
        self.report = report
        self.testCases = net_test_loader.testCases
        self.testClasses = net_test_loader.testClasses
        self.testDetails = net_test_loader.testDetails

        self.summary = {}

        # This will fire when all the measurements have been completed and
        # all the reports are done. Done means that they have either completed
        # successfully or all the possible retries have been reached.
        self.done = defer.Deferred()
        self.done.addCallback(self.doneNetTest)

        self.state = NetTestState(self.done)

    def __str__(self):
        return ' '.join(tc.name for tc, _ in self.testCases)

    def doneNetTest(self, result):
        if not self.summary:
            return
        print "Summary for %s" % self.testDetails['test_name']
        print "------------" + "-"*len(self.testDetails['test_name'])
        for test_class in self.testClasses:
            test_instance = test_class()
            test_instance.displaySummary(self.summary)

    def doneReport(self, report_results):
        """
        This will get called every time a report is done and therefore a
        measurement is done.

        The state for the NetTest is informed of the fact that another task has
        reached the done state.
        """
        self.state.taskDone()

        return report_results

    def makeMeasurement(self, test_instance, test_method, test_input=None):
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
        measurement = Measurement(test_instance, test_method, test_input)
        measurement.netTest = self

        if self.director:
            measurement.done.addCallback(self.director.measurementSucceeded,
                                         measurement)
            measurement.done.addErrback(self.director.measurementFailed,
                                        measurement)
        return measurement

    @defer.inlineCallbacks
    def initializeInputProcessor(self):
        for test_class, _ in self.testCases:
            test_class.inputs = yield defer.maybeDeferred(
                test_class().getInputProcessor
            )
            if not test_class.inputs:
                test_class.inputs = [None]

    def generateMeasurements(self):
        """
        This is a generator that yields measurements and registers the
        callbacks for when a measurement is successful or has failed.
        """

        for test_class, test_methods in self.testCases:
            # load the input processor as late as possible
            for input in test_class.inputs:
                measurements = []
                test_instance = test_class()
                test_instance.summary = self.summary
                for method in test_methods:
                    log.debug("Running %s %s" % (test_class, method))
                    measurement = self.makeMeasurement(
                        test_instance,
                        method,
                        input)
                    measurements.append(measurement.done)
                    self.state.taskCreated()
                    yield measurement

                # When the measurement.done callbacks have all fired
                # call the postProcessor before writing the report
                if self.report:
                    post = defer.DeferredList(measurements)

                    # Call the postProcessor, which must return a single report
                    # or a deferred
                    post.addCallback(test_instance.postProcessor)

                    def noPostProcessor(failure, report):
                        failure.trap(e.NoPostProcessor)
                        return report
                    post.addErrback(noPostProcessor, test_instance.report)
                    post.addCallback(self.report.write)

                if self.report and self.director:
                    # ghetto hax to keep NetTestState counts are accurate
                    [post.addBoth(self.doneReport) for _ in measurements]

        self.state.allTasksScheduled()


class NetTestCase(object):

    """
    This is the base of the OONI nettest universe. When you write a nettest
    you will subclass this object.

    * inputs: can be set to a static set of inputs. All the tests (the methods
      starting with the "test" prefix) will be run once per input. At every
      run the _input_ attribute of the TestCase instance will be set to the
      value of the current iteration over inputs.  Any python iterable object
      can be set to inputs.

    * inputFile: attribute should be set to an array containing the command
      line argument that should be used as the input file. Such array looks
      like this:

          ``["commandlinearg", "c", "default value" "The description"]``

      The second value of such arrray is the shorthand for the command line
      arg. The user will then be able to specify inputs to the test via:

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

    * usageOptions: a subclass of twisted.python.usage.Options for processing
        of command line arguments

    * localOptions: contains the parsed command line arguments.

    Quirks:
    Every class that is prefixed with test *must* return a
    twisted.internet.defer.Deferred.
    """
    name = "This test is nameless"
    author = "Jane Doe <foo@example.com>"
    version = "0.0.0"
    description = "Sorry, this test has no description :("

    inputs = None
    inputFile = None
    inputFilename = None

    report = {}

    usageOptions = usage.Options

    optParameters = None
    baseParameters = None
    baseFlags = None

    requiredTestHelpers = {}
    requiredOptions = []
    requiresRoot = False
    requiresTor = False

    localOptions = {}

    def _setUp(self):
        """
        This is the internal setup method to be overwritten by templates.
        """
        self.report = {}
        self.inputs = None

    def requirements(self):
        """
        Place in here logic that will be executed before the test is to be run.
        If some condition is not met then you should raise an exception.
        """
        pass

    def setUp(self):
        """
        Place here your logic to be executed when the test is being setup.
        """
        pass

    def postProcessor(self, measurements):
        """
        Subclass this to do post processing tasks that are to occur once all
        the test methods have been called once per input.
        postProcessing works exactly like test methods, in the sense that
        anything that gets written to the object self.report[] will be added to
        the final test report.
        You should also place in this method any logic that is required for
        generating the summary.
        """
        raise e.NoPostProcessor

    def displaySummary(self, summary):
        """
        This gets called after the test has run to allow printing out of a
        summary of the test run.
        """
        pass

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
                l = line.strip()
                # Skip empty lines
                if not l:
                    continue
                # Skip comment lines
                elif l.startswith('#'):
                    continue
                yield l

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


        If the operations to be done here are network related or blocking, they
        should be wrapped in a deferred. That is the return value of this
        method should be a :class:`twisted.internet.defer.Deferred`.

        Returns:
            a generator that will yield one item from the file based on the
            inputProcessor.
        """
        if self.inputFileSpecified:
            self.inputFilename = self.localOptions[self.inputFile[0]]
            return self.inputProcessor(self.inputFilename)

        if self.inputs:
            return self.inputs

        return None

    def _checkValidOptions(self):
        for option in self.localOptions:
            if option not in self.usageOptions():
                if not self.inputFile or option not in self.inputFile:
                    raise e.InvalidOption

    def _checkRequiredOptions(self):
        missing_options = []
        for required_option in self.requiredOptions:
            log.debug("Checking if %s is present" % required_option)
            if required_option not in self.localOptions or \
                    self.localOptions[required_option] is None:
                missing_options.append(required_option)
        if missing_options:
            raise e.MissingRequiredOption(missing_options, self)

    def __repr__(self):
        return "<%s inputs=%s>" % (self.__class__, self.inputs)
