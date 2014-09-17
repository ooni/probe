import os
import subprocess
from scapy.all import get_if_list

from ooni.utils import checkForRoot
from ooni.errors import InsufficientPrivileges

from twisted.trial import unittest

test_deck_old_format = """
- options:
    test_file: blocking/something
- options:
    test_file: blocking/for_fun
"""

test_deck_new_format = """
body:
  - nettest: blocking/something
  - nettest: blocking/for_fun
"""


class OoniNetworking(unittest.TestCase):
    def setUp(self):
        try:
            checkForRoot()
        except InsufficientPrivileges:
            self.skipTest('Superuser permissions are needed')
        self.filenames = []

    def tearDown(self):
        for filename in self.filenames:
            os.unlink(filename)
        subprocess.call(['ooninetworking', 'clean'])

    def test_add_nettest(self):
        subprocess.call(['ooninetworking', 'add_nettest', 'short'])
        ifaces = get_if_list()
        self.assertTrue(any(map(lambda x: 'short' in x, ifaces)))
        with open('/tmp/hosts.nmap') as f:
            lines = f.readlines()
        self.assertTrue(any(map(lambda x: 'short short' in x, lines)))

    def test_add_large_nettest(self):
        subprocess.call(['ooninetworking', 'add_nettest', 'extremely_large_iface_for_fun'])
        ifaces = get_if_list()
        self.assertTrue(any(map(lambda x: 'e_l_i_for_fun' in x, ifaces)))
        with open('/tmp/hosts.nmap') as f:
            lines = f.readlines()
        self.assertTrue(any(map(lambda x: 'extremely_large_iface_for_fun e_l_i_for_fun' in x, lines)))

    def test_del_nettest(self):
        orig_n_ifaces = len(get_if_list())
        subprocess.call(['ooninetworking', 'add_nettest', 'testing'])
        n_ifaces = len(get_if_list())
        self.assertEqual(orig_n_ifaces, n_ifaces - 1)
        subprocess.call(['ooninetworking', 'del_nettest', 'testing'])
        n_ifaces = len(get_if_list())
        self.assertEqual(orig_n_ifaces, n_ifaces)

    def test_add_deck_old_format(self):
        filename = 'test_deck'
        self.filenames.append(filename)
        with open(filename, 'w') as f:
            f.write(test_deck_old_format)

        subprocess.call(['ooninetworking', 'add_deck', 'test_deck'])
        ifaces = get_if_list()
        self.assertTrue(any(map(lambda x: 'something' in x, ifaces)))
        self.assertTrue(any(map(lambda x: 'for_fun' in x, ifaces)))

    def test_add_deck_new_format(self):
        filename = 'test_deck'
        self.filenames.append(filename)
        with open(filename, 'w') as f:
            f.write(test_deck_new_format)

        subprocess.call(['ooninetworking', 'add_deck', 'test_deck'])
        ifaces = get_if_list()
        self.assertTrue(any(map(lambda x: 'something' in x, ifaces)))
        self.assertTrue(any(map(lambda x: 'for_fun' in x, ifaces)))

    def test_del_deck(self):
        filename = 'test_deck'
        self.filenames.append(filename)
        with open(filename, 'w') as f:
            f.write(test_deck_new_format)

        orig_n_ifaces = len(get_if_list())
        subprocess.call(['ooninetworking', 'add_deck', 'test_deck'])
        n_ifaces = len(get_if_list())
        self.assertEqual(orig_n_ifaces, n_ifaces - 2)
        subprocess.call(['ooninetworking', 'del_deck', 'test_deck'])
        n_ifaces = len(get_if_list())
        self.assertEqual(orig_n_ifaces, n_ifaces)

    def test_clean(self):
        filename = 'test_deck'
        self.filenames.append(filename)
        with open(filename, 'w') as f:
            f.write(test_deck_new_format)

        orig_n_ifaces = len(get_if_list())
        subprocess.call(['ooninetworking', 'add_deck', 'test_deck'])
        subprocess.call(['ooninetworking', 'add_nettest', 'omg'])
        n_ifaces = len(get_if_list())
        self.assertNotEqual(orig_n_ifaces, n_ifaces)
        subprocess.call(['ooninetworking', 'clean'])
        n_ifaces = len(get_if_list())
        self.assertEqual(orig_n_ifaces, n_ifaces)
