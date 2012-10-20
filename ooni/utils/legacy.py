#-*- coding: utf-8 -*-
#
# legacy.py
# ---------
# Utilities for working with legacy OONI tests, i.e. tests which were created
# before the transition to the new twisted.trial based API.
#
# :authors: Isis Lovecruft, Arturo Filasto
# :license: see included LICENSE file
# :copyright: (c) 2012 Isis Lovecruft, Arturo Filasto, The Tor Project, Inc.
# :version: 0.1.0-pre-alpha


import inspect
import os
import yaml

from twisted.internet     import defer, reactor
from twisted.python       import log as tplog
from twisted.python.usage import Options as tpOptions

from ooni              import nettest
from ooni.plugoo.tests import OONITest
from ooni.utils        import log, date

class LegacyReporter(object):
    """
    Backwards compatibility class for creating a report object for results
    from a :class:`ooni.runner.LegacyTest`. A
    :class:`ooni.runner.LegacyReporter` object will eventually get wrapped in
    a list when :mod:`ooni.oonicli` calls
    :meth:`ooni.reporter.OONIReporter.stopTest`.

    :param report_target:
        The type of object to write results to, by default a list.
    """
    def __init__(self, report_target=[]):
        self.report_target = report_target
        if isinstance(self.report_target, dict):
            self._type = dict
        elif isinstance(self.report_target, list):
            self._type = list
        else:
            self._type = type(self.report_target)

    def __call__(self, info):
        if self._type is dict:
            self.report_target.update(info)
        elif self._type is list:
            self.report_target.append(info)
        else:
            log.debug("ADD A NEW REPORT_TARGET TYPE!!")

class LegacyOONITest(nettest.TestCase):
    """
    Converts an old test, which should be a subclass of
    :class:`ooni.plugoo.tests.OONITest`, to an :mod:`ooni.oonicli`
    compatible class.

    :param obj:
        An uninstantiated old test, which should be a subclass of
        :class:`ooni.plugoo.tests.OONITest`.
    :param config:
        A configured and instantiated :class:`twisted.python.usage.Options`
        class.
    :meth start_legacy_test:
        Handler for calling :meth:`ooni.plugoo.tests.OONITest.startTest`.
    """

    ## we need __bases__ because inspect.getmro() as well as
    ## zope.interface.implements() both expect it:
    from ooni.plugoo.tests import OONITest
    __bases__ = (OONITest, )

    def __getattr__(self, name):
        """
        Override of builtin getattr for :class:`ooni.runner.LegacyTest` so
        that method calls to a LegacyTest instance or its parent class
        OONITest do not return unhandled errors, but rather report that the
        method is unknown.
        """
        def __unknown_method__(*a):
            log.msg("Call to unknown method %s.%s" % (self.originalTest, name))
            if a:
                log.msg("Unknown method %s parameters: %s" % str(a))
        return __unknown_method__

    def find_missing_options(self):
        """
        In the case that our test is actually a class within a module named
        after itself, i.e. 'ooni.plugins.bridget.bridget', we want dynamic
        method discover so that we can search for the test's Options class.

        Example:
        Let's say we want the Options class, which is at
        ``ooni.plugins.bridget.bridget.options``. But in this case, our
        original_test variable isn't going to have an attribute named
        'options', because original_test is actually the *first* occurence of
        'bridget'.

        In other words, our original_test is actually the module, so we need
        to find the test, which is done with:

            getattr(original_test.__class__, test_class)

        After that, we've got our test stored as something like
        ``ooni.plugins.bridget.bridget`` and we need to find 'options' as an
        attribute under that, which is what

            options_finder = inspect.attrgetter('options')

        is used for. And the namespace stuff is just used for debugging edge
        cases where we totally can't find the options.

        :ivar original_class:
            The original subclass of OONITest, except that in this case,
            because our test is a module, what we have here is
            'ooni.plugins.bridget.BridgeTest', while we actually need
            something like 'ooni.plugins.bridget.bridget.BridgeTest' instead.
        :ivar class_string:
            The :ivar:`original_class` converted to a string.
        :ivar from_module:
            The parent module of :ivar:`original_class`, i.e.
            `ooni.plugins.bridget`.
        :ivar test_class:
            The last part of :ivar:`from_module`, ie. 'bridget'.
        :ivar options_finder:
            An instance of :meth:`inspect.attrgetter` which searches for
            methods within a test class named 'options'.
        """
        original_test  = self.originalTest
        original_class = original_test.__class__
        class_string   = str(original_class)
        from_module    = inspect.getmodule(original_class)
        test_class     = class_string.rsplit('.', 1)[1]
        options_finder = inspect.attrgetter('options')

        if self.was_named is False or self.name != test_class:
            log.msg("Discovered legacy test named %s ..." % test_class)
            setattr(self, 'name', test_class)

        try:
            namespace = globals()[class_string]
            log.debug("orginal namespace: %s" % namespace)
        except KeyError, keyerr:
            log.debug(keyerr)

        options = tpOptions
        try:
            options = options_finder(getattr(original_class, test_class))
        except AttributeError:
            self.__getattr__(test_class)
        except Exception, e:
            log.err(e)
        finally:
            return options()

    def __init__(self, obj, config):
        """
        xxx fill me in

        :param obj:
            An uninstantiated old test, which should be a subclass of
            :class:`ooni.plugoo.tests.OONITest`.
        :param config:
            A configured and instantiated
            :class:`twisted.python.usage.Options` class.
        :attr originalTest:
        :attr subArgs:
        :attr name:
        :ivar was_named:
        :attr subOptions:
        """
        super(LegacyOONITest, self).__init__()
        self.originalTest = obj
        self.start_time   = date.now()
        self.name         = 'LegacyOONITest'
        self.was_named    = False
        try:
            self.name      = self.originalTest.shortName
            self.was_named = True
        except AttributeError:
            if self.originalTest.name and self.originalTest.name != 'oonitest':
                self.name      = self.originalTest.name
                self.was_named = True

        if 'subArgs' in config:
            self.subArgs = config['subArgs']
        else:
            self.subArgs = (None, )
            log.msg("No suboptions to test %s found; continuing..."% self.name)

        try:
            self.subOptions = self.originalTest.options()
        except AttributeError:
            if self.was_named is False:
                self.subOptions = self.find_missing_options()
            else:
                self.subOptions = None
                log.msg("That test appears to have a name, but no options!")

        if self.subOptions is not None:
            if len(self.subArgs) > 0:
                self.subOptions.parseOptions(self.subArgs)
                self.local_options = self.subOptions
            else:
                print self.subOptions

        if 'reportfile' in config:
            self.reporter_file = config['reportfile']
        else:
            filename = str(self.name) + "-" + str(date.timestamp()) + ".yaml"
            self.reporter_file = os.path.join(os.getcwd(), filename)
        self.reporter = []
        self.report = LegacyReporter(report_target=self.reporter)

        self.legacy_test = self.originalTest(None, self.local_options,
                                             None, self.report)
        setattr(self.legacy_test, 'name', self.name)
        setattr(self.legacy_test, 'start_time', self.start_time)

        self.inputs = {}
        for keys, values in self.legacy_test.assets.items():
            self.inputs[keys] = values
        setattr(self.legacy_test, 'inputs', self.inputs)

    @defer.inlineCallbacks
    def run_with_args(self, args):
        """
        Handler for calling :meth:`ooni.plugoo.tests.OONITest.startTest` with
        each :param:`args` that, in the old framework, would have been
        generated one line at a time by
        :class:`ooni.plugoo.assets.Asset`. This function is wrapped with
        :meth:`twisted.internet.defer.inlineCallbacks` so that the result of
        each call to :meth:`ooni.plugoo.tests.OONITest.experiment` is returned
        immediately as :ivar:`returned`.
        """
        result = yield self.legacy_test.startTest(args)
        defer.returnValue(result)

def adapt_legacy_test(obj, config):
    """
    Wrapper function for taking a legacy OONITest class and converting it into
    a :class:`LegacyTest`, which is a variant of the new
    :class:`ooni.nettest.TestCase` and is compatible with
    :mod:`ooni.oonicli`. This allows for backward compatibility of old OONI
    tests.

    :param obj:
        An uninstantiated old test, which should be a subclass of
        :class:`ooni.plugoo.tests.OONITest`.
    :param config:
        A configured and instantiated :class:`twisted.python.usage.Options`
        class.
    :return:
        A :class:`LegacyOONITest`.
    """
    return LegacyOONITest(obj, config)

def report_legacy_test_to_file(legacy_test, file=None):
    """
    xxx this function current does not get used, and could easily be handled
        by ooni.runner.loadTestsAndOptions, or some other function in
        ooni.runner.

    xxx fill me in
    """
    reporter_file = legacy_test.reporter_file

    if file is not None:
        base = os.path.dirname(os.path.abspath(file))
        if base.endswith("ooni") or base == os.getcwd():
            reporter_file = file
        else:
            log.msg("Writing to %s not allowed, using default file %s."
                    % (base, reporter_file))

    yams = yaml.safe_dump(legacy_test.reporter)
    with open(reporter_file, 'a') as rosemary:
        rosemary.write(yams)
        rosemary.flush()
        log.msg("Finished reporting.")

def log_legacy_test_results(result, legacy_test, args):
    """
    Callback function for deferreds in :func:`start_legacy_test` which
    handles updating the legacy_test's :class:`legacy_test.report`.

    :param result:
        The possible result of a deferred which has been returned from
        :meth:`ooni.plugoo.test.OONITest.experiment` and
        :meth:`ooni.plugoo.test.OONITest.control`.
    :param legacy_test:
        The :class:`LegacyOONITest` which we're processing.
    :param args:
        The current inputs which we're giving to legacy_test.startTest().
    :return:
        The :param:`legacy_test`.
    """
    if result:
        legacy_test.report({args: result})
        log.debug("Legacy test %s with args:\n%s\nreturned result:\n%s"
                  % (legacy_test.name, args, result))
    else:
        legacy_test.report({args: None})
        log.debug("No results return for %s with args:\n%s"
                  % (legacy_test.name, args))
    return legacy_test

def start_legacy_test(legacy_test):
    """
    This is the main function which should be used to call a legacy test, it
    handles parsing the deprecated :class:`ooni.plugoo.assets.Asset` items as
    inputs, and calls back to a custom, backwards-compatible Reporter.

    For each input to the legacy_test, this function creates a
    :class:`twisted.internet.defer.Deferred` which has already received its
    :meth:`callback`. The end result is a
    :class:`twisted.internet.defer.gatherResults` of all the outcomes of
    :param:`legacy_test` for each of the inputs.

    :param legacy_test:
        A :class:`LegacyOONITest` to process.
    :ivar results:
        A list of :class:`twisted.internet.defer.Deferred`s which gets
        processed as a :class:`twisted.internet.defer.DeferredList`.
    :ivar current_input:
        The input we are current working on, i.e. what would have been 'args'
        (as in, 'experiment(args)') in the old design.
    :return:
        A :class:`twisted.internet.defer.gatherResults`.
    """
    results = []
    current_input = {}

    if len(legacy_test.inputs) > 0:
        for keys, values in legacy_test.inputs:
            for value in values:
                current_input[keys] = value
                log.debug("Running %s with args: %s"
                          % (legacy_test.name, current_input))
                d = legacy_test.run_with_args(current_input)
                d.addCallback(log_legacy_test_results, legacy_test,
                              current_input)
                d.addErrback(tplog.err)
                results.append(d)
    else:
        current_input['zero_input_test'] = True
        log.debug("Running %s with current input: %s"
                  % (legacy_test.name, current_input))
        d = legacy_test.run_with_args(current_input)
        d.addCallback(log_legacy_test_results, legacy_test, current_input)
        d.addErrback(tplog.err)
        results.append(d)

    dlist = defer.gatherResults(results)
    return dlist
