import os
import re
import time
import sys

from twisted.internet import defer
from twisted.python.filepath import FilePath
from twisted.trial.runner import filenameToModule
from twisted.python import failure, usage, reflect

from ooni import __version__ as ooniprobe_version, errors
from ooni import otime
from ooni.tasks import Measurement
from ooni.utils import log, sanitize_options, randomStr
from ooni.utils.net import hasRawSocketPermission
from ooni.settings import config
from ooni.geoip import probe_ip

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

    return {
        'description': description,
        'value': default,
        'required': required,
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


def normalizeTestName(test_class_name):
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
    information = {
        'id': test_id,
        'name': test_class.name,
        'description': test_class.description,
        'version': test_class.version,
        'arguments': getArguments(test_class),
        'simple_options': test_class.simpleOptions,
        'path': net_test_file
    }
    return information


def usageOptionsFactory(test_name, test_version):

    class UsageOptions(usage.Options):
        optParameters = []
        optFlags = []

        synopsis = "{} {} [options]".format(
            os.path.basename(sys.argv[0]),
            test_name
        )

        def opt_version(self):
            """
            Display the net_test version and exit.
            """
            log.msg("{} version: {}".format(test_name, test_version))
            sys.exit(0)

    return UsageOptions

def netTestCaseFactory(test_class, local_options):
    class NetTestCaseWithLocalOptions(test_class):
        localOptions = local_options
    return NetTestCaseWithLocalOptions

ONION_INPUT_REGEXP = re.compile("(httpo://[a-z0-9]{16}\.onion)/input/(["
                                "a-z0-9]{64})$")

class NetTestLoader(object):
    method_prefix = 'test'
    collector = None
    yamloo = True
    requiresTor = False

    def __init__(self, options, test_file=None, test_string=None,
                 annotations=None):
        self.options = options
        if annotations is None:
            annotations = {}
        if not isinstance(annotations, dict):
            log.warn("BUG: Annotations is not a dictionary. Resetting it.")
            annotations = {}
        self.annotations = annotations
        self.annotations['platform'] = self.annotations.get('platform',
                                                            config.platform)

        self.requiresTor = False

        self.testName = ""
        self.testVersion = ""
        self.reportId = None

        self.testHelpers = {}
        self.missingTestHelpers = []
        self.usageOptions = None
        self.inputFiles = []

        self._testCases = []
        self.localOptions = None

        if test_file:
            self.loadNetTestFile(test_file)
        elif test_string:
            self.loadNetTestString(test_string)

    def getTestDetails(self):
        return {
            'probe_asn': probe_ip.geodata['asn'],
            'probe_cc': probe_ip.geodata['countrycode'],
            'probe_ip': probe_ip.geodata['ip'],
            'probe_city': probe_ip.geodata['city'],
            'software_name': 'ooniprobe',
            'software_version': ooniprobe_version,
            # XXX only sanitize the input files
            'options': sanitize_options(self.options),
            'annotations': self.annotations,
            'data_format_version': '0.2.0',
            'test_name': self.testName,
            'test_version': self.testVersion,
            'test_helpers': self.testHelpers,
            'test_start_time': otime.timestampNowLongUTC(),
            # XXX We should deprecate this key very soon
            'input_hashes': [],
            'report_id': self.reportId
        }

    def getTestCases(self):
        """
        Specialises the test_classes to include the local options.
        :return:
        """
        test_cases = []
        for test_class, test_method in self._testCases:
            test_cases.append((netTestCaseFactory(test_class,
                                                  self.localOptions),
                               test_method))
        return test_cases

    def _accumulateInputFiles(self, test_class):
        if not test_class.inputFile:
            return

        key = test_class.inputFile[0]
        filename = self.localOptions[key]
        if not filename:
            return

        input_file = {
            'key': key,
            'test_options': self.localOptions,
            'filename': None
        }
        m = ONION_INPUT_REGEXP.match(filename)
        if m:
            raise e.InvalidInputFile("Input files hosted on hidden services "
                                     "are no longer supported")
        else:
            input_file['filename'] = filename
        self.inputFiles.append(input_file)

    def _accumulateTestOptions(self, test_class):
        """
        Accumulate the optParameters and optFlags for the NetTestCase class
        into the usageOptions of the NetTestLoader.
        """
        if getattr(test_class.usageOptions, 'optParameters', None):
            for parameter in test_class.usageOptions.optParameters:
                # XXX should look into if this is still necessary, seems like
                # something left over from a bug in some nettest.
                # In theory optParameters should always have a length of 4.
                if len(parameter) == 5:
                    parameter.pop()
                self.usageOptions.optParameters.append(parameter)

        if getattr(test_class, 'inputFile', None):
            self.usageOptions.optParameters.append(test_class.inputFile)

        if getattr(test_class, 'baseParameters', None):
            for parameter in test_class.baseParameters:
                self.usageOptions.optParameters.append(parameter)

        if getattr(test_class, 'baseFlags', None):
            for flag in test_class.baseFlags:
                self.usageOptions.optFlags.append(flag)

    def parseLocalOptions(self):
        """
        Parses the localOptions for the NetTestLoader.
        """
        self.localOptions = self.usageOptions()
        try:
            self.localOptions.parseOptions(self.options)
        except usage.UsageError:
            tb = sys.exc_info()[2]
            raise e.OONIUsageError(self), None, tb

    def _checkTestClassOptions(self, test_class):
        if test_class.requiresRoot and not hasRawSocketPermission():
            raise e.InsufficientPrivileges
        if test_class.requiresTor:
            self.requiresTor = True
        self._checkRequiredOptions(test_class)
        self._setTestHelpers(test_class)
        test_instance = netTestCaseFactory(test_class, self.localOptions)()
        test_instance.requirements()

    def _setTestHelpers(self, test_class):
        for option, name in test_class.requiredTestHelpers.items():
            if self.localOptions.get(option, None):
                self.testHelpers[option] = self.localOptions[option]

    def _checkRequiredOptions(self, test_class):
        missing_options = []
        for required_option in test_class.requiredOptions:
            log.debug("Checking if %s is present" % required_option)
            if required_option not in self.localOptions or \
                    self.localOptions[required_option] is None:
                missing_options.append(required_option)
        missing_test_helpers = [opt in test_class.requiredTestHelpers.keys()
                                for opt in missing_options]
        if len(missing_test_helpers) and all(missing_test_helpers):
            self.missingTestHelpers = map(lambda x:
                                            (x, test_class.requiredTestHelpers[x]),
                                          missing_options)
            raise e.MissingTestHelper(missing_options, test_class)
        elif missing_options:
            raise e.MissingRequiredOption(missing_options, test_class)

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
            test_cases.extend(self._getTestMethods(item))

        if not test_cases:
            raise e.NoTestCasesFound

        self._setupTestCases(test_cases)

    def loadNetTestFile(self, net_test_file):
        """
        Load NetTest from a file.
        """
        test_cases = []
        module = filenameToModule(net_test_file)
        for __, item in getmembers(module):
            test_cases.extend(self._getTestMethods(item))

        if not test_cases:
            raise e.NoTestCasesFound

        self._setupTestCases(test_cases)

    def _setupTestCases(self, test_cases):
        """
        Creates all the necessary test_cases (a list of tuples containing the
        NetTestCase (test_class, test_method))

        example:
            [(test_classA, [test_method1,
                            test_method2,
                            test_method3,
                            test_method4,
                            test_method5]),
            (test_classB, [test_method1,
                           test_method2])]

        Note: the inputs must be valid for test_classA and test_classB.

        net_test_file:
            is either a file path or a file like object that will be used to
            generate the test_cases.
        """
        test_class, _ = test_cases[0]
        self.testName = normalizeTestName(test_class.name)
        self.testVersion = test_class.version
        self._testCases = test_cases

        self.usageOptions = usageOptionsFactory(self.testName,
                                                self.testVersion)

        if config.reports.unique_id is True:
            self.reportId = randomStr(64)

        for test_class, test_methods in self._testCases:
            self._accumulateTestOptions(test_class)

    def checkOptions(self):
        self.parseLocalOptions()
        test_options_exc = None
        usage_options = self._testCases[0][0].usageOptions
        for test_class, test_methods in self._testCases:
            try:
                self._accumulateInputFiles(test_class)
                self._checkTestClassOptions(test_class)
                if usage_options != test_class.usageOptions:
                    raise e.IncoherentOptions(usage_options.__name__,
                                              test_class.usageOptions.__name__)
            except Exception as exc:
                test_options_exc = exc

        if test_options_exc is not None:
            raise test_options_exc

    def _getTestMethods(self, item):
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
            if self.allTasksDone.called:
                log.err("allTasksDone was already called. This is probably a bug.")
            else:
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

    def __init__(self, test_cases, test_details, report):
        """
        net_test_loader:
             an instance of :class:ooni.nettest.NetTestLoader containing
             the test to be run.

        report:
            an instance of :class:ooni.reporter.Reporter
        """
        self.report = report

        self.testDetails = test_details
        self.testCases = test_cases

        self.summary = {}

        # This will fire when all the measurements have been completed and
        # all the reports are done. Done means that they have either completed
        # successfully or all the possible retries have been reached.
        self.done = defer.Deferred()
        self.done.addCallback(self.doneNetTest)

        self.state = NetTestState(self.done)

    def __str__(self):
        return ' '.join(tc.name for tc, _ in self.testCases)

    def uniqueClasses(self):
        classes = []
        for test_class, test_method in self.testCases:
            if test_class not in classes:
                classes.append(test_class)
        return classes

    def doneNetTest(self, result):
        if self.summary:
            log.msg("Summary for %s" % self.testDetails['test_name'])
            log.msg("------------" + "-"*len(self.testDetails['test_name']))
            for test_class in self.uniqueClasses():
                test_instance = test_class()
                test_instance.displaySummary(self.summary)
        if self.testDetails["report_id"]:
            log.msg("Report ID: %s" % self.testDetails["report_id"])

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
    def initialize(self):
        for test_class, _ in self.testCases:
            # Initialize Input Processor
            test_class.inputs = yield defer.maybeDeferred(
                test_class().getInputProcessor
            )

            # Run the setupClass method
            yield defer.maybeDeferred(
                test_class.setUpClass
            )

    def generateMeasurements(self):
        """
        This is a generator that yields measurements and registers the
        callbacks for when a measurement is successful or has failed.

        FIXME: If this generator throws exception TaskManager scheduler is
        irreversibly damaged.
        """

        for test_class, test_methods in self.testCases:
            # load a singular input processor for all instances
            all_inputs = test_class.inputs
            for test_input in all_inputs:
                measurements = []
                test_instance = test_class()
                # Set each instances inputs to a singular input processor
                test_instance.inputs = all_inputs
                test_instance._setUp()
                test_instance.summary = self.summary
                for method in test_methods:
                    try:
                        measurement = self.makeMeasurement(
                            test_instance,
                            method,
                            test_input)
                    except Exception:
                        log.exception(failure.Failure())
                        log.err('Failed to run %s %s %s' % (test_instance, method, test_input))
                        continue # it's better to skip single measurement...
                    log.debug("Running %s %s" % (test_instance, method))
                    measurements.append(measurement.done)
                    self.state.taskCreated()
                    yield measurement

                # This is to skip setting callbacks on measurements that
                # cannot be run.
                if len(measurements) == 0:
                    continue

                # When the measurement.done callbacks have all fired
                # call the postProcessor before writing the report
                if self.report:
                    post = defer.DeferredList(measurements)

                    @post.addBoth
                    def set_runtime(results):
                        runtime = time.time() - test_instance._start_time
                        for _, m in results:
                            m.testInstance.report['test_runtime'] = runtime
                        test_instance.report['test_runtime'] = runtime
                        return results

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

    usageOptions = usage.Options

    optParameters = None
    baseParameters = None
    baseFlags = None

    requiredTestHelpers = {}
    requiredOptions = []
    requiresRoot = False
    requiresTor = False

    simpleOptions = {}

    localOptions = {}

    @classmethod
    def setUpClass(cls):
        """
        You can override this hook with logic that should be run once before
        any test method in the NetTestCase is run.
        This can be useful to populate class attribute that should be valid
        for all the runtime of the NetTest.
        """
        pass

    def _setUp(self):
        """
        This is the internal setup method to be overwritten by templates.
        It gets called once for every input.
        """
        self.report = {}

    def requirements(self):
        """
        Place in here logic that will be executed before the test is to be run.
        If some condition is not met then you should raise an exception.
        """
        pass

    def setUp(self):
        """
        Place here your logic to be executed when the test is being setup.
        It gets called once every test method + input.
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

        return [None]

    def __repr__(self):
        return "<%s inputs=%s>" % (self.__class__, self.inputs)


def nettest_to_path(path, allow_arbitrary_paths=False):
    """
    Takes as input either a path or a nettest name.

    The nettest name may either be prefixed by the category of the nettest (
    blocking, experimental, manipulation or third_party) or not.

    Args:

        allow_arbitrary_paths:
            allow also paths that are not relative to the nettest_directory.

    Returns:

        full path to the nettest file.
    """
    if allow_arbitrary_paths and os.path.exists(path):
        return path

    test_name = path.rsplit("/", 1)[-1]
    test_categories = [
        "blocking",
        "experimental",
        "manipulation",
        "third_party"
    ]
    nettest_dir = FilePath(config.nettest_directory)
    found_path = None
    for category in test_categories:
        p = nettest_dir.preauthChild(os.path.join(category, test_name) + '.py')
        if p.exists():
            if found_path is not None:
                raise Exception("Found two tests named %s" % test_name)
            found_path = p.path

    if not found_path:
        raise e.NetTestNotFound(path)
    return found_path
