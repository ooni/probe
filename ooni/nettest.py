# -*- encoding: utf-8 -*-
#
#     nettest.py
# ------------------->
#
# :authors: Arturo "hellais" Filastò <art@fuffa.org>,
#           Isis Lovecruft <isis@torproject.org>
# :licence: see LICENSE
# :copyright: 2012 Arturo Filasto, Isis Lovecruft
# :version: 0.1.0-alpha
#
# <-------------------

from functools import partial
import sys
import os
import itertools
import traceback

from twisted.trial import unittest, itrial, util
from twisted.internet import defer, utils
from twisted.python import usage

from ooni.utils import log

pyunit = __import__('unittest')


class InputTestSuite(pyunit.TestSuite):
    """
    This in an extension of a unittest test suite. It adds support for inputs
    and the tracking of current index via idx.
    """

    # This is used to keep track of the tests that are associated with our
    # special test suite
    _tests = None
    def run(self, result, idx=0):
        log.debug("Running test suite")
        self._idx = idx
        while self._tests:
            if result.shouldStop:
                log.debug("Detected that test should stop")
                log.debug("Stopping...")
                break
            test = self._tests.pop(0)

            try:
                log.debug("Setting test attributes with %s %s" %
                            (self.input, self._idx))

                test.input = self.input
                test._idx = self._idx
            except Exception, e:
                log.debug("Error in setting test attributes")
                log.debug("This is probably because the test case you are "\
                          "running is not a nettest")
                log.debug(e)

            log.debug("Running test")
            # XXX we may want in a future to put all of these tests inside of a
            # thread pool and run them all in parallel
            test(result)
            log.debug("Ran.")

            self._idx += 1
        return result

class NetTestAdaptor(unittest.TestCase):
    """
    XXX fill me in
    """

    # @classmethod
    # def __new__(cls, *args, **kwargs):
    #     try:
    #         setUpClass()
    #     except Exception, e:
    #         log.debug("NetTestAdaptor: constructor could not find setUpClass")
    #         log.err(e)
    #     return super( NetTestAdaptor, cls ).__new__(cls, *args, **kwargs)

    def __init__(self, *args, **kwargs):
        """
        If you override me, you must call

            ``super(NetTestCase, self).__init__(*args, **kwargs)``

        at the beginning of your __init__ method. Keyword arguments passed to
        the above statement become attributes of the adaptor, and can be used
        to alter the logic of input handling and parent class instantiation.
        Therefore, You probably do not need to pass me any keyword arguments
        when calling me, i.e. using ``(*args, **kwargs)`` will work just fine.
        """
        log.debug("NetTestAdaptor: created")
        if kwargs:
            if 'methodName' in kwargs:
                log.debug("NetTestAdaptor: found 'methodName' in kwargs")
                log.debug("NetTestAdaptor: calling unittest.TestCase.__init()")
                super( NetTestAdaptor, self ).__init__(
                    methodName=kwargs['methodName'] )
            else:
                log.debug("NetTestAdaptor: calling unittest.TestCase.__init()")
                super( NetTestAdaptor, self ).__init__( )

            for key, value in kwargs.items():     ## Let subclasses define their
                if key != 'methodName':           ## instantiation without
                    if not hasattr(self, key):    ## overriding parent classes
                        log.debug("NetTestAdaptor: calling setattr(self,%s,%s)"
                                  % (key, value) )
                        setattr(self, key, value)

        #setattr(self, "copyattr", __copy_attr__)

        ## Internal attribute copies:
        #self._input_parser = copyattr("inputParser", alt=__input_parser__)
        #self._nettest_name = copyattr("name", alt="NetTestAdaptor"))

        #self.setUpClass(self.__class__)

        #if hasattr(self, parsed_inputs):
        #    self.inputs = self.parsed_inputs
        #else:
        #    log.debug("Unable to find parsed inputs")

    @staticmethod
    def __copyattr__(obj, old, new=None, alt=None):
        """
        Assign me to a new attribute name to have a copy of the old
        attribute, if it exists.

        Example:
        >>> self.sun = "black"
        >>> self._watermelon = __copyattr__(self, "sun")
        >>> self._clocknoise = __copyattr__(self, "sound")
        >>> print self._watermelon
            black
        >>> print self._clocknoise

        :param old:
            A string representing the name of the old attribute
        :param new:
            (Optional) A string to set as the new attribute name.
        :param alt:
            (Optional) An alternate value to return if the old
            attribute is not found.
        :return:
            If :param:`old` is found, I return it's value.

            If :param:`old` is not found:
                If :param:`alt` is given, I return :param:`alt`.
                Else, I return None.

            If :param:`new` is set, I do not return anything, and
            instead I set the new attribute's name to :param:`name`
            and it's value to the value which I would have otherwise
            returned.
        """
        if not new:
            if not alt:
                if hasattr(obj, old):
                    return getattr(obj, old)
                return
            else:
                if hasattr(obj, old):
                    return getattr(obj, old)
                return alt
        else:
            if not alt:
                if hasattr(obj, old):
                    _copy = getattr(obj, old)
                else:
                    copy = None
                setattr(obj, new, _copy)
            else:
                if hasattr(obj, old):
                    _copy = getattr(obj, old)
                else:
                    _copy = alt
                setattr(obj, new, _copy)

    def copyattr(self, *args, **kwargs):
        if len(args) >= 1:
           _copy = partial(__copyattr__, args[0])
           if len(args) == 2:
               return _copy(new=args[1])
           elif len(args) == 3:
               return _copy(new=args[1], alt=args[2])
           elif kwargs:
               return _copy(kwargs)
        else:
           return

    @staticmethod
    def __input_parser__(one_input): return one_input

    @classmethod
    def __get_inputs__(cls):
        """
        I am called during class setup and you probably should not override
        me. I gather the internal inputs from :class:`NetTestCase` attributes
        and pass them through :meth:`NetTestCase.inputParser`.  If you are
        looking for a way to parse inputs from inputFile, see
        :meth:`inputParser`. If :class:`NetTestCase` has an attribute
        :attr:`inputFile`, I also handle opening that file, striping each line
        of whitespace, and then sending the line to
        :meth:`NetTestCase.inputParser`.

        All inputs which I find, both statically set inputs and those returned
        from processing an inputFile, I add to a list :ivar:`parsed`, after
        parsing them. I return :ivar:`parsed`:

        :ivar parsed:
            A list of parsed inputs.
        :return:
            :ivar:`parsed`.
        """
        parsed = []

        if cls._raw_inputs:
            if isinstance(cls._raw_inputs, (list, tuple,)):
                if len(cls._raw_inputs) > 0:
                    if len(cls._raw_inputs) == 1 and cls._raw_inputs[0] is None:
                        pass       ## don't burn cycles on testing null inputs
                    else:
                        log.msg("Received direct inputs:\n%s" % cls._raw_inputs)
                        parsed.extend(
                            [cls._input_parser(x) for x in cls._raw_inputs])
            elif isinstance(cls._raw_inputs, str):
                separated = cls._raw_inputs.translate(None, ',') ## space delineates
                inputlist = separated.split(' ')
                parsed.extend([cls._input_parser(x) for x in inputlist])
            else:
                log.debug("inputs not string or list; type: %s"
                          % type(cls._raw_inputs))

        if cls.subarg_inputs:
            log.debug("NetTestAdaptor: __get_inputs__ found subarg_inputs=%s"
                      % cls.subarg_inputs)
            parsed.extend([cls._input_parser(x) for x in cls.subarg_inputs])

        if cls._input_file:
            try:
                log.debug("NetTestAdaptor: __get_inputs__ Opening input file")
                fp = open(cls._input_file)
            except:
                log.debug("NetTestAdaptor: __get_inputs__ Couldn't open input file")
            else:
                log.debug("NetTestAdaptor: __get_inputs__ Running input file processor")
                lines = [line.strip() for line in fp.readlines()]
                fp.close()

                ## add to what we've already parsed, if any:
                log.debug("NetTestAdaptor: __get_inputs__ Parsing lines from input file")
                parsed.extend([cls._input_parser(ln) for ln in lines])
        else:
            log.debug("NetTestAdaptor: %s specified that it doesn't need inputFile."
                      % cls._nettest_name)

        return parsed

    @classmethod
    def __getopt__(cls, parseArgs=None):
        """
        Constuctor for a custom t.p.usage.Options class, per NetTestCase.

        old code from runner.py:
            opts = Options()
            opts.parseOptions(config['subArgs'])
            cls.localOptions = opts
        """
        if cls._testopt_params or cls._input_file:
            if not cls._testopt_params:
                cls._testopt_params = []

            if cls._input_file:
                cls._testopt_params.append(cls.input_file)

        class NetTestOptions(usage.Options):
            """Per NetTestCase Options class."""
            optParameters     = cls._testopt_params
            optFlags          = cls._testopt_flags
            subOptions        = cls._sub_options
            subCommands       = cls._sub_commands
            defaultSubCommand = cls._default_subcmd
            ## XXX i'm not sure if this part will work:
            parseArgs         = lambda a: cls.subarg_inputs.append(a)

            def opt_version(self):
                """Display test version and exit."""
                print "Test version: ", cls._nettest_version
                sys.exit(0)

        options = NetTestOptions()
        return options

        #if cls._input_file:
        #    cls._input_file = cls.options[cls._input_file[0]]

    @classmethod
    def addSubArgToInputs(cls, subarg):
        cls.subarg_inputs.append(subarg)

    @classmethod
    def buildOptions(cls, from_global):
        log.debug("NetTestAdaptor: getTestOptions called")
        options = cls.__getopt__()
        log.debug("NetTestAdaptor: getTestOptions: cls.options = %s"
                  % options)
        options.parseOptions(from_global)
        setattr(cls, "local_options", options)
        log.debug("NetTestAdaptor: getTestOptions: cls.local_options = %s"
                  % cls.local_options)

    @classmethod
    def setUpClass(cls):
        """
        Create a NetTestCase. To add futher setup steps before a set of tests
        in a TestCase instance run, create a function called 'setUp'.

        Class attributes, such as `report`, `optParameters`, `name`, and
        `author` should be overriden statically as class attributes in any
        subclass of :class:`ooni.nettest.NetTestCase`, so that the calling
        functions during NetTestCase class setup can handle them correctly.
        """

        log.debug("NetTestAdaptor: setUpClass called")

        ## These internal inputs are for handling inputs and inputFile
        cls._raw_inputs   = cls.__copyattr__(cls, "inputs")
        cls._input_file   = cls.__copyattr__(cls, "inputFile")
        cls._input_parser = cls.__copyattr__(cls, "inputParser",
                                             alt=cls.__input_parser__)
        cls._nettest_name = cls.__copyattr__(cls, "name", alt="NetTestAdaptor")

        ## This creates a class attribute with all of the parsed inputs,
        ## which the instance will later set to be `self.inputs`.
        cls.parsed_inputs = cls.__get_inputs__()
        cls.subarg_inputs = cls.__copyattr__(cls, "subarg_inputs",
                                             alt=[])

        ## XXX we should handle options generation here
        cls._testopt_params  = cls.__copyattr__(cls, "optParameters")
        cls._testopt_flags   = cls.__copyattr__(cls, "optFlags")
        cls._sub_options     = cls.__copyattr__(cls, "subOptions")
        cls._sub_commands    = cls.__copyattr__(cls, "subCommands")
        cls._default_subcmd  = cls.__copyattr__(cls, "defaultSubCommand")
        cls._nettest_version = cls.__copyattr__(cls, "version")

class NetTestCase(NetTestAdaptor):
    """
    This is the monad of the OONI nettest universe. When you write a nettest
    you will subclass this object.

    * inputs: can be set to a static set of inputs. All the tests (the methods
      starting with the "test_" prefix) will be run once per input.  At every
      run the _input_ attribute of the TestCase instance will be set to the
      value of the current iteration over inputs.  Any python iterable object
      can be set to inputs.

    * inputFile: attribute should be set to an array containing the command
      line argument that should be used as the input file. Such array looks
      like this:

          ``["commandlinearg", "c", "The description"]``

      The second value of such arrray is the shorthand for the command line
      arg.  The user will then be able to specify inputs to the test via:

          ``ooniprobe mytest.py --commandlinearg path/to/file.txt``

      or

          ``ooniprobe mytest.py -c path/to/file.txt``


    * inputParser: should be set to a function that takes as argument an
      iterable containing test inputs and it simply parses those inputs and
      returns them back to test instance.

    * name: should be set to the name of the test.

    * author: should contain the name and contact details for the test author.
      The format for such string is as follows:

          ``The Name <email@example.com>``

    * version: is the version string of the test.

    * requiresRoot: set to True if the test must be run as root.
    """
    name = "I Did Not Change The Name"
    author = "Jane Doe <foo@example.com>"
    version = "0.0.0"

    inputFile = None
    inputs    = [None]

    report = {}
    report['errors'] = []

    optParameters = None
    optFlags = None
    subCommands = None
    requiresRoot = False

    def deferSetUp(self, ignored, result):
        """
        If we have the reporterFactory set we need to write the header. If
        such method is not present we will only run the test skipping header
        writing.
        """
        if result.reporterFactory.firstrun:
            log.debug("Detecting first run. Writing report header.")
            d1 = result.reporterFactory.writeHeader()
            d2 = unittest.TestCase.deferSetUp(self, ignored, result)
            dl = defer.DeferredList([d1, d2])
            return dl
        else:
            log.debug("Not first run. Running test setup directly")
            return unittest.TestCase.deferSetUp(self, ignored, result)

    def inputParser(self, inputs):
        """Replace me with a custom function for parsing inputs."""
        log.debug("Running custom input processor")
        return inputs

    def getOptions(self):
        log.debug("Getting options for test")

        if self.local_options:
            log.debug("NetTestCase: getOptions: self.local_options=%s"
                      % str(self.local_options))
        else:
            log.debug("could not find cls.localOptions!")

        return {'inputs': self.parsed_inputs,
                'name': self.name,
                'version': self.version}
        # if options:
        #     return options
        # else:
        #     ## is this safe to do? it might turn Hofstaeder...
        #     return self.__dict__
        ####################
        ## original return
        ####################
        #return {'inputs': self.inputs,
        #        'name': self.name,
        #        'version': self.version}
    '''
    def __repr__(self):
        return "<%s inputs=%s>" % (self.__class__, self.inputs)
    '''
