import os

from twisted.trial.runner import filenameToModule
from twisted.python import usage, reflect

from ooni.tasks import Measurement
from ooni.utils import log

from inspect import getmembers
from StringIO import StringIO

class NetTest(object):
    director = None
    method_prefix = 'test'

    def __init__(self, net_test_file, inputs, options, report):
        """
        net_test_file:
            is a file object containing the test to be run.

        inputs:
            is a generator containing the inputs to the net test.

        options:
            is a dict containing the options to be passed to the net test.
        """
        self.test_cases = self.loadNetTest(net_test_file)
        self.inputs = inputs
        self.options = options

        self.report = report

    def loadNetTest(self, net_test_object):
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

        net_test_object:
            is a file like object that will be used to generate the test_cases.
        """
        try:
            if os.path.isfile(net_test_object):
                return self._loadNetTestFile(net_test_object)
        except TypeError:
            if isinstance(net_test_object, StringIO) or \
                isinstance(net_test_object, str):
                return self._loadNetTestString(net_test_object)

    def _loadNetTestString(self, net_test_string):
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
        for test_input in self.inputs:
            for test_class, test_method in self.test_cases:
                measurement = Measurement(test_class, test_method, test_input)
                measurement.netTest = self
                yield measurement

class NoPostProcessor(Exception):
    pass

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

    def _checkRequiredOptions(self):
        for required_option in self.requiredOptions:
            log.debug("Checking if %s is present" % required_option)
            if not self.localOptions[required_option]:
                raise usage.UsageError("%s not specified!" % required_option)

    def _processOptions(self):
        if self.inputFilename:
            inputProcessor = self.inputProcessor
            inputFilename = self.inputFilename
            class inputProcessorIterator(object):
                """
                Here we convert the input processor generator into an iterator
                so that we can run it twice.
                """
                def __iter__(self):
                    return inputProcessor(inputFilename)
            self.inputs = inputProcessorIterator()

        return {'inputs': self.inputs,
                'name': self.name, 'version': self.version
               }

    def __repr__(self):
        return "<%s inputs=%s>" % (self.__class__, self.inputs)

