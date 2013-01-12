from twisted.internet.task import CooperativeTask
from twisted.internet import defer
from ooni.reporter import OONIBReporter, YAMLReporter, OONIBReportError
from ooni.utils import log
import time
from twisted.internet.task import cooperate

class NetTestTask(CooperativeTask):
    """
    The object produced by a NetTestTaskFactory.

    A NetTestTask wraps a test_ callable with its options and input unit.

    """
    def __init__(self, test_case, test_input, oonib_reporter=None, yaml_reporter=None):
        test_class, test_method = test_case
        #log.debug("Running %s with %s..." % (test_method, test_input))
        self.oonib_reporter = oonib_reporter
        self.oonib_reporter = yaml_reporter
        self.test_instance = test_class()
        self.test_instance.input = test_input
        self.test_instance.report = {}
        self.test_instance._start_time = time.time()
        self.test_instance._setUp()
        self.test_instance.setUp()
        self.test = getattr(self.test_instance, test_method)

    # XXX: override CoordinatedTask methods
    def start(self):  #???
        d = defer.maybeDeferred(self.test)
        d.addCallback(self.test_done)
        d.addErrback(self.test_error)
        return d

    def write_report(self):
        if not self.oonib_reporter:
            return self.yaml_reporter.testDone(self.test_instance, str(self.test))
        d1 = self.oonib_reporter.testDone(self.test_instance, str(self.test))
        d2 = self.yaml_reporter.testDone(self.test_instance, str(self.test))
        dl = defer.DeferredList([d1, d2])
        @dl.addErrback
        def reportingFailed(failure):
            log.err("Error in reporting %s" % self.test)
            log.exception(failure)
        return dl

    def test_done(self, result):
        log.msg("Finished running %s" % self.test)
        log.debug("Deferred callback result: %s" % result)
        return self.write_report()

    def test_error(self, failure):
        log.err("Error in running %s" % self.test)
        log.exception(failure)
        return self.write_report()

    #XXX: does not implement tests_done!

class NetTestTaskFactory(object):
    def __init__(self, test_cases, input_unit_list):
        self.input_unit_list = input_unit_list
        self.inputs = self.generate_inputs()
        self.test_cases = test_cases

    def __iter__(self):
        return self

    def next(self):
        return self.inputs.next()
        # XXX: raise exception or fire callback when inputs are exhausted

    def generate_inputs(self):
        for input_unit in self.input_unit_list:
            for test_case in self.test_cases:
                yield NetTestTask(test_case, input_unit)

@defer.inlineCallbacks
def runTestCases(test_cases, options, cmd_line_options):

    log.debug("Running %s" % test_cases)
    log.debug("Options %s" % options)
    log.debug("cmd_line_options %s" % dict(cmd_line_options))

    test_inputs = options['inputs']

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

    nettest_task_factory = NetTestTaskFactory(test_cases, test_inputs)

    #XXX: resume is not supported!
    try:
        #XXX: override the default cooperator, set up own scheduler
        #XXX: add callback when tasks are all exhausted
        for nettest_task in nettest_task_factory.generate_inputs():
            nettest_task.yaml_reporter = yaml_reporter
            nettest_task.oonib_reporter = oonib_reporter
            log.debug("Running %s with input unit %s" % (nettest_task,
                        nettest_task.test_instance.input))
            # feed the cooperator
            nettest_task.start()

    except Exception:
        log.exception("Problem in running test")
