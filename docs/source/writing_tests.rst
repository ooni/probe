Writing OONI tests
==================


The OONI testing API is heavily influenced and partially based on the python
:class:`unittest` module and :class:`twsted.trial`.


Test Cases
----------

The atom of OONI Testing is called a Test Case. A test case class may contain
multiple Test Functions.

.. autoclass:: ooni.nettest.NetTestCase
    :noindex:

:class:`ooni.nettest.TestCase` is a subclass of :class:`unittest.TestCase` so
the assert methods that apply to :class:`unittest.TestCase` will also apply to
:class:`ooni.nettest.TestCase`.

If the test you plan to write is not listed on the `Tor OONI trac page
<https://trac.torproject.org/projects/tor/wiki/doc/OONI/Tests>`_, you should
add it to the list and following the `test template
<https://trac.torproject.org/projects/tor/wiki/doc/OONI/Tests/TestTemplate>`_
write up a description about it.


Inputs
------

Inputs are what is given as input to every iteration of the Test Case. You have
100 inputs, then every test case will be run 100 times.

To configure a static set of inputs you should define the
:class:`ooni.nettest.TestCase` attribute ``inputs``. The test will be run ``len(inputs)`` times. Any iterable object is a valid ``inputs`` attribute.

If you would like to have inputs be determined from a user specified input
file, then you must set the ``inputFile`` attribute. This is an array that
specifies what command line option may be used to control this value.

By default the ``inputProcessor`` is set to read the file line by line and
strip newline characters. To change this behavior you must set the
``inputProcessor`` attribute to a function that takes as arugment a file
descriptor and yield the next item. The default ``inputProcessor`` looks like
this::


    def lineByLine(fp):
        for x in fp.readlines():
            yield x.strip()
        fp.close()


Test Functions
--------------

These shall be defined inside of your :class:`ooni.nettest.TestCase` subclass.
These will be class methods.

To add data to the test report you may write directly to the report object like
so::

    def my_test_function():
        result = do_something()
        self.report['something'] = result

OONI will then handle the writing of the data to the final test report.

To access the current input you can use the ``input`` attribute, for example::

    def my_test_with_input():
        do_something_with_input(self.input)

This will at each iteration over the list of inputs do something with the
input.

Backward compatibility
----------------------

All ooni tests written using the experiment(), control() pattern are supported,
but all new tests should no longer be written using such pattern.

Code in protocols should be refactored to follow the new API.

