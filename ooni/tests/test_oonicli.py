import os
import sys
import yaml
import signal
import socket

from twisted.internet import base, defer
from twisted.trial import unittest

from ooni.tests import is_internet_connected
from ooni.settings import config
from ooni.oonicli import runWithDirector

def verify_header(header):
    assert 'input_hashes' in header.keys()
    assert 'options' in header.keys()
    assert 'probe_asn' in header.keys()
    assert 'probe_cc' in header.keys()
    assert 'probe_ip' in header.keys()
    assert 'software_name' in header.keys()
    assert 'software_version' in header.keys()
    assert 'test_name' in header.keys()
    assert 'test_version' in header.keys()

def verify_entry(entry):
    assert 'input' in entry

   
class TestRunDirector(unittest.TestCase):
    def setUp(self):
        if not is_internet_connected():
            self.skipTest("You must be connected to the internet to run this test")
        config.tor.socks_port = 9050
        config.tor.control_port = None
        with open('example-input.txt', 'w+') as f:
            f.write('http://torproject.org/\n')
            f.write('http://bridges.torproject.org/\n')
            f.write('http://blog.torproject.org/\n')
    
    def tearDown(self):
        os.remove('test_report.yaml')
        os.remove('example-input.txt')
    
    @defer.inlineCallbacks
    def run_test(self, test_name, args, verify_function):
        output_file = 'test_report.yaml'
        sys.argv = ['', '-n', '-o', output_file, test_name]
        sys.argv.extend(args)
        yield runWithDirector(False, False)
        with open(output_file) as f:
            entries = yaml.safe_load_all(f)
            header = entries.next()
            try:
                first_entry = entries.next()
            except StopIteration:
                raise Exception("Missing entry in report")
        verify_header(header)
        verify_entry(first_entry)
        verify_function(first_entry)

    @defer.inlineCallbacks
    def test_http_requests(self):
        def verify_function(entry):
            assert 'body_length_match' in entry
            assert 'body_proportion' in entry
            assert 'control_failure' in entry
            assert 'experiment_failure' in entry
            assert 'factor' in entry
            assert 'headers_diff' in entry
            assert 'headers_match' in entry
        yield self.run_test('blocking/http_requests', 
                      ['-u', 'http://torproject.org/'],
                      verify_function)

    @defer.inlineCallbacks
    def test_http_requests_with_file(self):
        def verify_function(entry):
            assert 'body_length_match' in entry
            assert 'body_proportion' in entry
            assert 'control_failure' in entry
            assert 'experiment_failure' in entry
            assert 'factor' in entry
            assert 'headers_diff' in entry
            assert 'headers_match' in entry
        yield self.run_test('blocking/http_requests', 
                      ['-f', 'example-input.txt'],
                      verify_function)

    @defer.inlineCallbacks
    def test_dnsconsistency(self):
        def verify_function(entry):
            assert 'queries' in entry
            assert 'control_resolver' in entry
            assert 'tampering' in entry
            assert len(entry['tampering']) == 1
        yield self.run_test('blocking/dnsconsistency', 
                            ['-b', '8.8.8.8:53', 
                             '-t', '8.8.8.8',
                             '-f', 'example-input.txt'],
                            verify_function)

    @defer.inlineCallbacks
    def test_http_header_field_manipulation(self):
        def verify_function(entry):
            assert 'agent' in entry
            assert 'requests' in entry
            assert 'socksproxy' in entry
            assert 'tampering' in entry
            assert 'header_field_name' in entry['tampering']
            assert 'header_field_number' in entry['tampering']
            assert 'header_field_value' in entry['tampering']
            assert 'header_name_capitalization' in entry['tampering']
            assert 'header_name_diff' in entry['tampering']
            assert 'request_line_capitalization' in entry['tampering']
            assert 'total' in entry['tampering']

        yield self.run_test('manipulation/http_header_field_manipulation', 
                            ['-b', 'http://64.9.225.221'],
                           verify_function)
