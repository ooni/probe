import yaml
import json
import time
from mock import MagicMock

from twisted.internet import defer
from twisted.trial import unittest

from ooni.utils.net import StringProducer
from ooni import errors as e
from ooni.reporter import YAMLReporter, OONIBReporter

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
    'probe_asn': 'AS0'
}

oonib_new_report_message = {
    'report_id': "2014-01-29T202038Z_AS0_"+"A"*50,
    'backend_version': "1.0"
}

oonib_generic_error_message = {
    'error': 'generic-error'
}

class TestYAMLReporter(unittest.TestCase):
    def setUp(self):
        pass

    def test_write_report(self):
        test = MockTest()

        y_reporter = YAMLReporter(test_details)
        y_reporter.createReport()
        y_reporter.testDone(test, 'spam')
        with open(y_reporter.report_path) as f:
            report_entries = yaml.safe_load_all(f)
            # Check for keys in header
            entry = report_entries.next()
            assert all(x in entry for x in ['test_name', 'test_version'])

            entry = report_entries.next()
            # Check for first entry of report
            assert all(x in entry \
                       for x in ['report_content', 'input', \
                                 'test_name', 'test_started', \
                                 'test_runtime'])

class TestOONIBReporter(unittest.TestCase):
    
    def setUp(self):
        self.mock_response = {}
        self.collector_address = 'http://example.com'

        self.oonib_reporter = OONIBReporter(test_details, self.collector_address)
        self.oonib_reporter.agent = MagicMock()
        self.mock_agent_response = MagicMock()
        def deliverBody(body_receiver):
            body_receiver.dataReceived(json.dumps(self.mock_response))
            body_receiver.connectionLost(None)
        self.mock_agent_response.deliverBody = deliverBody
        self.oonib_reporter.agent.request.return_value = defer.succeed(self.mock_agent_response)
    
    @defer.inlineCallbacks
    def test_create_report(self):
        self.mock_response = oonib_new_report_message
        yield self.oonib_reporter.createReport()
        assert self.oonib_reporter.reportID == oonib_new_report_message['report_id']

    @defer.inlineCallbacks
    def test_create_report_failure(self):
        self.mock_response = oonib_generic_error_message
        self.mock_agent_response.code = 406
        yield self.assertFailure(self.oonib_reporter.createReport(), e.OONIBReportCreationError)

    @defer.inlineCallbacks
    def test_write_report_entry(self):
        req = {'content': 'something'}
        yield self.oonib_reporter.writeReportEntry(req)
        assert self.oonib_reporter.agent.request.called

