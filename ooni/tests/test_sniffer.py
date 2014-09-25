from twisted.trial import unittest

from mock import MagicMock, patch

from ooni.sniffer import pcapdnet_installed, ip_generator, ScapySniffer


class SnifferTestCase(unittest.TestCase):
    def setUp(self):
        self.old_setup_interface = ScapySniffer.setup_interface
        ScapySniffer.setup_interface = MagicMock()
        test_details = {'test_name': 'dummy_test', 'start_time': 1.0}
        self.sniffer = ScapySniffer(test_details)

    def tearDown(self):
        ScapySniffer.setup_interface = self.old_setup_interface

    def test_pcapdnet_installed(self):
        self.assertTrue(pcapdnet_installed())

    def test_gen_short_iface(self):
        self.sniffer.test_name = 'some_test'
        self.sniffer.gen_iface()
        self.assertEqual(self.sniffer.iface, 'some_test')

    def test_gen_very_large_iface(self):
        self.sniffer.test_name = 'some_test_with_a_really_long_name'
        self.sniffer.gen_iface()
        self.assertEqual(self.sniffer.iface, 's_t_w_a_r_l_n')

    def test_gen_large_iface(self):
        self.sniffer.test_name = 'this_is_a_long_name'
        self.sniffer.gen_iface()
        self.assertEqual(self.sniffer.iface, 't_i_a_long_name')

    def test_gen_real_iface(self):
        self.sniffer.test_name = 'http_invalid_request_line'
        self.sniffer.gen_iface()
        self.assertEqual(self.sniffer.iface, 'http_i_r_line')


class IPGeneratorTestCase(unittest.TestCase):
    def test_next_ip_unique(self):
        one = ip_generator.next_ip()
        another = ip_generator.next_ip()
        self.assertNotEqual(one, another)
