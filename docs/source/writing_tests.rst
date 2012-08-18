.. OONI documentation master file.

==================
Writing OONI tests
==================

OONIProbe tests can be written in two modes: blocking or non-blocking.

Going the blocking route is not advised and all tests in the end should end up
being written in the non-blocking way.

A good way to understand how to write a test is also to take a look at the OONI
Test Interface in the following files:

* ooni/plugoo/interface.py

* ooni/plugoo/tests.py

Writing non-blocking tests
--------------------------

To bootstrap the process of creating a new tests you can run the scaffolding
script in ooni/scaffolding.py.

This will create a new plugin with the specified name inside of ooni/plugins/.

