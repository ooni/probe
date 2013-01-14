from twisted.trial import unittest
from ooni.reporter import Report, YAMLReporter, OONIBReporter
from ooni.managers import ReportEntryManager
from ooni.nettest import NetTest
from ooni.tasks import TaskMediator

mockReportOptions = {'name':'foo_test', 'version': '0.1'}

class TestYAMLReporter(unittest.TestCase):
    def setUp(self):
        pass

    def test_create_yaml_reporter(self):

        YAMLReporter.reportFilePrefix = "spam"
        YAMLReporter.options = mockReportOptions
        report = Report([YAMLReporter])
        #XXX: calls createReport on init. is that what we want?
        report.reportEntryManager = ReportEntryManager()
        allTasksDone = defer.Deferred()
        report.taskmediator = TaskMediator()

    #def test_create_yaml_report(self):
    #    # should create a YAML report
    #    raise NotImplementedError

    def test_write_yaml_report(self):
        YAMLReporter.reportFilePrefix = "spam"
        YAMLReporter.options = mockReportOptions
        report = Report([YAMLReporter])
        #XXX: fire createReport on init. is that what we want?
        report.reportEntryManager = ReportEntryManager()
        report.write("HAI")

    def test_write_yaml_report_before_create(self):
       # should write to YAML report before it has been created
       # the write should not occur until after the created callback has fired
       raise NotImplementedError

    def test_yaml_report_completed(self):
       # should test that a report will complete successfully
       # it should fire a callback after the report.finish method is called,
       # XXX: a report should not be finalized until after all pending
       # writes have completed
       raise NotImplementedError

    def test_write_after_completed(self):
       # try to call write after a report is completed/finalized. it must fail
       # it should also fail in the sense that as long as the finalize-report has
       # been called no additional reports entries can be added, but
       # existing/pending entries should be completed before the report
       # finalized callback is fired
       raise NotImplementedError


#class OONIBReporter(unittest.TestCase):
#    def setUp(self):
#        #XXX set up a dummy OONIB backend
#        pass
#
#    def test_create_oonib_reporter(self):
#        # should instance a OONIB reporter
#        raise NotImplementedError
#
#    def test_create_oonib_report(self):
#        # should create a YAML report
#        raise NotImplementedError
#
#    def test_write_oonib_report(self):
#        # should write to YAML report
#        raise NotImplementedError
#
#    def test_write_oonib_report_before_create(self):
#        # should write to YAML report before it has been created
#        # the write should not occur until after the created callback has fired
#        raise NotImplementedError
