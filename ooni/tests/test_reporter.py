import os
import yaml
import json
import time
from mock import MagicMock

from twisted.internet import defer
from twisted.trial import unittest

from ooni import errors as e
from ooni.tests.mocks import MockCollectorClient
from ooni.reporter import YAMLReporter, OONIBReporter, OONIBReportLog



class MockTest(object):
    _start_time = time.time()
    report = {'report_content': 'ham'}
    input = 'spam'


test_details = {
    'test_name': 'spam',
    'test_version': '1.0',
    'software_name': 'spam',
    'software_version': '1.0',
    'input_hashes': [],
    'probe_asn': 'AS0',
    'probe_cc': 'ZZ',
    'test_start_time': '2016-01-01 22:33:11',
    'data_format_version': '0.2.0'
}

oonib_new_report_message = {
    'report_id': "20140129T202038Z_AS0_" + "A" * 50,
    'backend_version': "1.0",
    'supported_formats': ["yaml", "json"]
}

# This is used for testing legacy collectors
oonib_new_report_yaml_message = {
    'report_id': "20140129T202038Z_AS0_" + "A" * 50,
    'backend_version': "1.0"
}


oonib_generic_error_message = {
    'error': 'generic-error'
}


class TestYAMLReporter(unittest.TestCase):

    def setUp(self):
        self.filename = ""

    def tearDown(self):
        if self.filename != "":
            os.remove(self.filename)

    def test_write_report(self):
        y_reporter = YAMLReporter(test_details, 'dummy-report.yaml')
        y_reporter.createReport()
        with open(y_reporter.report_path) as f:
            self.filename = y_reporter.report_path
            report_entries = yaml.safe_load_all(f)
            # Check for keys in header
            entry = report_entries.next()
            assert all(x in entry for x in ['test_name', 'test_version'])


class TestOONIBReporter(unittest.TestCase):

    def setUp(self):
        self.mock_response = {}

        def mockRequest(method, urn, genReceiver, *args, **kw):
            receiver = genReceiver(None, None)
            return defer.maybeDeferred(receiver.body_processor,
                                       json.dumps(self.mock_response))

        mock_collector_client = MockCollectorClient('http://example.com')
        mock_collector_client._request = mockRequest

        self.oonib_reporter = OONIBReporter(
            test_details,
            mock_collector_client
        )

    @defer.inlineCallbacks
    def test_create_report(self):
        self.mock_response = oonib_new_report_message
        yield self.oonib_reporter.createReport()
        self.assertEqual(self.oonib_reporter.reportId,
                         oonib_new_report_message['report_id'])

    @defer.inlineCallbacks
    def test_create_report_failure(self):
        self.mock_response = oonib_generic_error_message
        yield self.assertFailure(self.oonib_reporter.createReport(),
                                 e.OONIBReportCreationError)

    @defer.inlineCallbacks
    def test_write_report_entry(self):
        self.mock_response = oonib_new_report_message
        yield self.oonib_reporter.createReport()
        req = {'content': 'something'}
        yield self.oonib_reporter.writeReportEntry(req)

    @defer.inlineCallbacks
    def test_write_report_entry_in_yaml(self):
        self.mock_response = oonib_new_report_yaml_message
        yield self.oonib_reporter.createReport()
        req = {'content': 'something'}
        yield self.oonib_reporter.writeReportEntry(req)

class TestOONIBReportLog(unittest.TestCase):

    def setUp(self):
        self.report_log = OONIBReportLog('report_log')
        self.report_log.create_report_log()

    def tearDown(self):
        os.remove(self.report_log.file_name)

    @defer.inlineCallbacks
    def test_report_created(self):
        yield self.report_log.created("path_to_my_report.yaml",
                                             'httpo://foo.onion',
                                             'someid')
        with open(self.report_log.file_name) as f:
            report = yaml.safe_load(f)
            assert "path_to_my_report.yaml" in report

    @defer.inlineCallbacks
    def test_concurrent_edit(self):
        d1 = self.report_log.created("path_to_my_report1.yaml",
                                            'httpo://foo.onion',
                                            'someid1')
        d2 = self.report_log.created("path_to_my_report2.yaml",
                                            'httpo://foo.onion',
                                            'someid2')
        yield defer.DeferredList([d1, d2])
        with open(self.report_log.file_name) as f:
            report = yaml.safe_load(f)
            assert "path_to_my_report1.yaml" in report
            assert "path_to_my_report2.yaml" in report

    @defer.inlineCallbacks
    def test_report_closed(self):
        yield self.report_log.created("path_to_my_report.yaml",
                                             'httpo://foo.onion',
                                             'someid')
        yield self.report_log.closed("path_to_my_report.yaml")

        with open(self.report_log.file_name) as f:
            report = yaml.safe_load(f)
            assert "path_to_my_report.yaml" not in report

    @defer.inlineCallbacks
    def test_report_creation_failed(self):
        yield self.report_log.creation_failed("path_to_my_report.yaml",
                                                     'httpo://foo.onion')
        with open(self.report_log.file_name) as f:
            report = yaml.safe_load(f)
        assert "path_to_my_report.yaml" in report
        assert report["path_to_my_report.yaml"]["status"] == "creation-failed"

    @defer.inlineCallbacks
    def test_list_reports(self):
        yield self.report_log.creation_failed("failed_report.yaml",
                                              'httpo://foo.onion')
        yield self.report_log.created("created_report.yaml",
                                      'httpo://foo.onion', 'XXXX')

        assert len(self.report_log.reports_in_progress) == 1
        assert len(self.report_log.reports_incomplete) == 0
        assert len(self.report_log.reports_to_upload) == 1
