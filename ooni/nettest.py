import os

from twisted.trial.runner import filenameToModule
from twisted.python import usage, reflect

from ooni.tasks import Measurement
from ooni.utils import log, checkForRoot, NotRootError

from inspect import getmembers
from StringIO import StringIO

class NoTestCasesFound(Exception):
    pass

class NetTest(object):
    measurementManager = None
    method_prefix = 'test'

    def __init__(self, net_test_file, options, report):
        """
        net_test_file:
            is a file object containing the test to be run.

        options:
            is a dict containing the options to be passed to the net test.
        """
        self.options = options
        self.report = report
        self.test_cases = self.loadNetTest(net_test_file)

    def start(self):
        """
        Set up tests and start running.
        Start tests and generate measurements.
        """
        self.setUpNetTestCases()
        self.measurementManager.schedule(self.generateMeasurements())

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

        return test_cases

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
            for method in methods:
                test_cases.append((item, self.method_prefix + method))
        except (TypeError, AssertionError):
            pass
        return test_cases

    def succeeded(self, measurement):
        """
        This gets called when a measurement has failed.
        """
        self.report.write(measurement)

    def generateMeasurements(self):
        """
        This is a generator that yields measurements and sets their timeout
        value and their netTest attribute.
        """
        for test_class, test_method in self.test_cases:
            for test_input in test_class.inputs:
                measurement = Measurement(test_class, test_method,
                        test_input, self)
                measurement.netTest = self
                yield measurement

    def setUpNetTestCases(self):
        """
        Call processTest and processOptions methods of each NetTestCase
        """
        test_classes = set([])
        for test_class, test_method in self.test_cases:
            test_classes.add(test_class)

        for klass in test_classes:
            klass.localOptions = self.options

            test_instance = klass()
            if test_instance.requiresRoot:
                checkForRoot()
            test_instance._checkRequiredOptions()
            test_instance._checkValidOptions()

            klass.inputs = test_instance.getInputProcessor()

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

    def inputProcessor(self, filename=None):
        """
        You may replace this with your own custom input processor. It takes as
        input a file name.

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
        if filename:
            fp = open(filename)
            for x in fp.xreadlines():
                yield x.strip()
            fp.close()
        else:
            pass

    def getInputProcessor(self):
        """
        This method must be called after all options are validated by
        _checkValidOptions and _checkRequiredOptions, which ensure that
        if the inputFile is a required option it will be present.
        """
        if self.inputFile:
            if self.inputFile[0] in self.localOptions:
                self.inputFilename = self.localOptions[self.inputFile[0]]

                inputProcessor = self.inputProcessor
                inputFilename = self.inputFilename

                class inputProcessorIterator(object):
                    """
                    Here we convert the input processor generator into an iterator
                    so that we can run it twice.
                    """
                    def __iter__(self):
                        return inputProcessor(inputFilename)

                return inputProcessorIterator()

        return iter(())

    def _checkValidOptions(self):
        for option in self.localOptions:
            if option not in self.usageOptions():
                if not self.inputFile or option not in self.inputFile:
                    raise InvalidOption

    def _checkRequiredOptions(self):
        for required_option in self.requiredOptions:
            log.debug("Checking if %s is present" % required_option)
            if required_option not in self.localOptions:
               raise MissingRequiredOption

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
