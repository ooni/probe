import os
import yaml
import json
import time
import shutil
import tempfile

from twisted.internet import defer
from twisted.trial import unittest

from ooni.tests.bases import ConfigTestCase
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

class TestOONIBReportLog(ConfigTestCase):

    def setUp(self):
        super(TestOONIBReportLog, self).setUp()
        self.measurement_id = '20160727T182604Z-ZZ-AS0-dummy'
        self.config.measurements_directory = tempfile.mkdtemp()
        self.measurement_dir = os.path.join(
            self.config.measurements_directory,
            self.measurement_id
        )
        self.report_log_path = os.path.join(self.measurement_dir,
                                            'report_log.json')
        os.mkdir(self.measurement_dir)
        self.report_log = OONIBReportLog()

    def tearDown(self):
        shutil.rmtree(self.measurement_dir)
        super(TestOONIBReportLog, self).tearDown()

    @defer.inlineCallbacks
    def test_report_created(self):
        yield self.report_log.created(self.measurement_id, {})
        with open(self.report_log_path) as f:
            report = json.load(f)
            self.assertEqual(report['status'], 'created')

    @defer.inlineCallbacks
    def test_report_closed(self):
        yield self.report_log.created(self.measurement_id, {})
        yield self.report_log.closed(self.measurement_id)

        self.assertFalse(os.path.exists(self.report_log_path))

    @defer.inlineCallbacks
    def test_report_creation_failed(self):
        yield self.report_log.creation_failed(self.measurement_id, {})
        with open(self.report_log_path) as f:
            report = json.load(f)
        self.assertEqual(report["status"], "creation-failed")

    @defer.inlineCallbacks
    def test_list_reports_in_progress(self):
        yield self.report_log.created(self.measurement_id, {})
        in_progress = yield self.report_log.get_in_progress()
        incomplete = yield self.report_log.get_incomplete()
        self.assertEqual(len(incomplete), 0)
        self.assertEqual(len(in_progress), 1)

    @defer.inlineCallbacks
    def test_list_reports_to_upload(self):
        yield self.report_log.creation_failed(self.measurement_id, {})
        incomplete = yield self.report_log.get_incomplete()
        to_upload = yield self.report_log.get_to_upload()
        self.assertEqual(len(incomplete), 0)
        self.assertEqual(len(to_upload), 1)
