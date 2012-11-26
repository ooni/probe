import unittest
from ooni.inputunit import InputUnit, InputUnitFactory

def dummyGenerator():
    for x in range(100):
        yield x

class TestInputUnit(unittest.TestCase):
    def test_input_unit_factory(self):
        inputUnit = InputUnitFactory(range(100))
        for i in inputUnit:
            self.assertEqual(len(list(i)), inputUnit.inputUnitSize)

    def test_input_unit(self):
        inputs = range(100)
        inputUnit = InputUnit(inputs)
        idx = 0
        for i in inputUnit:
            idx += 1

        self.assertEqual(idx, 100)

    def test_input_unit_factory_length(self):
        inputUnitFactory = InputUnitFactory(range(100))
        l1 = len(inputUnitFactory)
        l2 = sum(1 for _ in inputUnitFactory)
        self.assertEqual(l1, 10)
        self.assertEqual(l2, 10)

