import unittest
from ooni.inputunit import InputUnit, InputUnitFactory

class TestInputUnit(unittest.TestCase):
    def test_input_unit_factory(self):
        inputs = range(100)
        inputUnit = InputUnitFactory(inputs)
        for i in inputUnit:
            self.assertEqual(len(list(i)), inputUnit.inputUnitSize)

    def test_input_unit(self):
        inputs = range(100)
        inputUnit = InputUnit(inputs)
        idx = 0
        for i in inputUnit:
            idx += 1

        self.assertEqual(idx, 100)
