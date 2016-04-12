import os
import sys
import yaml

from twisted.internet import defer

from ooni.tests import is_internet_connected
from ooni.tests.bases import ConfigTestCase
from ooni.settings import config
from ooni.oonicli import runWithDirector
from ooni.utils.net import hasRawSocketPermission


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

config_includepcap = """
basic:
    logfile: ~/.ooni/ooniprobe.log
privacy:
    includeip: false
    includeasn: true
    includecountry: true
    includecity: false
    includepcap: true
reports:
    pcap: null
    collector: null
advanced:
    geoip_data_dir: /usr/share/GeoIP
    debug: false
    interface: auto
    start_tor: false
    measurement_timeout: 60
    measurement_retries: 2
    measurement_concurrency: 10
    reporting_timeout: 80
    reporting_retries: 3
    reporting_concurrency: 15
    data_dir: %s
    oonid_api_port: 8042
tor:
    socks_port: 9050

""" % config.data_directory


class TestRunDirector(ConfigTestCase):
    timeout = 220

    def setUp(self):
        super(TestRunDirector, self).setUp()
        if not is_internet_connected():
            self.skipTest("You must be connected to the internet to run this test")
        elif not hasRawSocketPermission():
            self.skipTest("You must run this test as root or have the capabilities "
            "cap_net_admin,cap_net_raw+eip")
        config.tor.socks_port = 9050
        config.tor.control_port = None
        self.filenames = ['example-input.txt']
        with open('example-input.txt', 'w+') as f:
            f.write('http://torproject.org/\n')
            f.write('http://bridges.torproject.org/\n')
            f.write('http://blog.torproject.org/\n')

    def tearDown(self):
        super(TestRunDirector, self).tearDown()
        for filename in self.filenames:
            if os.path.exists(filename):
                os.remove(filename)
        self.filenames = []

    @defer.inlineCallbacks
    def run_helper(self, test_name, args, verify_function):
        output_file = 'test_report.yaml'
        self.filenames.append(os.path.join(config.reports_directory, output_file))
        sys.argv = ['', '-n', '-o', output_file, test_name]
        sys.argv.extend(args)
        yield runWithDirector(False, False)
        with open(os.path.join(config.reports_directory, output_file)) as f:
            entries = yaml.safe_load_all(f)
            header = entries.next()
            try:
                first_entry = entries.next()
            except StopIteration:
                raise Exception("Missing entry in report")
        verify_header(header)
        verify_entry(first_entry)
        verify_function(first_entry)
        sys.argv = oldargv

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

        yield self.run_helper('blocking/http_requests',
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

        yield self.run_helper('blocking/http_requests',
                              ['-f', 'example-input.txt'],
                              verify_function)

    @defer.inlineCallbacks
    def test_dnsconsistency(self):
        def verify_function(entry):
            assert 'queries' in entry
            assert 'control_resolver' in entry
            assert 'errors' in entry
            assert 'inconsistent' in entry
            assert 'failures' in entry
            assert 'successful' in entry
            assert len(entry['inconsistent']) == 0

        yield self.run_helper('blocking/dns_consistency',
                              ['-b', '8.8.8.8:53',
                               '-t', '8.8.8.8',
                               '-f', 'example-input.txt'],
                              verify_function)

    @defer.inlineCallbacks
    def test_http_header_field_manipulation(self):
        self.skipTest("This test requires a property configured backend")
        def verify_function(entry):
            assert 'agent' in entry
            assert 'requests' in entry
            assert 'socksproxy' in entry
            assert 'errors' in entry

        yield self.run_helper('manipulation/http_header_field_manipulation',
                              ['-b', 'http://4.15.35.157:80'],
                              verify_function)

    @defer.inlineCallbacks
    def test_sniffing_activated(self):
        self.skipTest("Not properly set packet capture?")
        filename = os.path.abspath('test_report.pcap')
        self.filenames.append(filename)
        conf_file = os.path.abspath('fake_config.conf')
        with open(conf_file, 'w') as cfg:
            cfg.writelines(config_includepcap)
        self.filenames.append(conf_file)

        def verify_function(_):
            assert os.path.exists(filename)
            self.assertGreater(os.stat(filename).st_size, 0)
        yield self.run_helper('blocking/http_requests',
                              ['-f', 'example-input.txt'],
                              verify_function, ooni_args=['-f', conf_file])
        config.scapyFactory.connectionLost('')
