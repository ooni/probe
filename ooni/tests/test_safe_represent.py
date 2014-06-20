import yaml

from twisted.trial import unittest

from ooni.reporter import OSafeDumper

from scapy.all import IP, UDP


class TestScapyRepresent(unittest.TestCase):
    def test_represent_scapy(self):
        data = IP() / UDP()
        yaml.dump_all([data], Dumper=OSafeDumper)


