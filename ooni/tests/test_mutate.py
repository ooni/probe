import unittest
from ooni.kit import daphn3


class TestDaphn3(unittest.TestCase):
    def test_mutate_string(self):
        original_string = '\x00\x00\x00'
        mutated = daphn3.daphn3MutateString(original_string, 1)
        self.assertEqual(mutated, '\x00\x01\x00')

    def test_mutate_daphn3(self):
        original_dict = [{'client': '\x00\x00\x00'},
                         {'server': '\x00\x00\x00'}]
        mutated_dict = daphn3.daphn3Mutate(original_dict, 1, 1)
        self.assertEqual(mutated_dict, [{'client': '\x00\x00\x00'},
                                        {'server': '\x00\x01\x00'}])

