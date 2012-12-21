Architecture
============
:Author: Arturo Filastò
:Contact: art@torproject.org
:Copyright: This document has been placed in the public domain.

The goal of this document is provide an overview of how ooni works, what are
it's pieces and how they interact with one another.

Keep in mind that this is the *big picture* and not all of the features and
compontent detailed here are implemented.
To get an idea of what is implemented and with what sort of quality see the
`Implementation status`_ section of this page.

The two main components of ooni are `oonib`_ and `ooniprobe`_.

.. image:: _static/images/ooniprobe-architecture.png
    :width: 700px

ooniprobe
---------

ooniprobe the client side component of ooni that is responsible for performing
measurements on the to be tested network.

The main design goals for ooniprobe are:

Test specification decoupling
.............................

By this I mean that the definition of the test should be as loosely coupled to
the code that is used for running the test.

This is achieved via what are called **Test Templates**. Test Templates a high
level interface to the test developer specific to the protocol they are writing
a test for.
The Test template will then be responsible for implementing the measurement
logic, generic error handling and the formatting of reports using a format that
is standard for the type of test that is being run.

This does not mean that test developers should only include in their report
tests what is generated for them by the test template, but, when using Test
Templates, the report will always be a superset of what is provided by the test
template.

For example the a test based on the :class:`ooni.templates.httpt.HTTPTest` test
template will always have the list of HTTP requests performed and the responses
received, but a developer may with to include inside of their report the
checksum of the of the content as is show in the example in `Writing Tests
<writing_tests.html>`_.

Support for high concurrency
............................

By this I mean that we want to be able to scan through big lists as fast as
possible.

The problem when doing censorship measurement tests is that you often have to
deal with very big lists and going over these lists sequentially is slow and
time consuming.

For this purpose we have chosen to use the `Twisted networking framework
<http://twistedmatrix.org>`_. The reasons for using Twisted are:

  * It is stable and has been around for many year (version 1.0 came out 11 years XXX citation)

  * People in the Tor community use it

  * People in the Python community use it

If you have an argument for which you believe Twisted is not a good idea, I
would love to know :).

Notes:
.. XXX

Running lot's of tests concurrently can reduce their accuracy.  The strategy
for dealing with this involves doing proper error handling and adjusting the
concurrency window over time if the amount of error rates increases.

Currently the level of concurrency for tests is implemented inside of
:class:`ooni.inputunit`_, but we do not expose to the user a way of setting
this. Such feature will be something that will be controllable via the
ooniprobe API.

Standardization
...............

.. TODO

oonib
-----

This is the backend component of OONI. It is responsible for exposing `test
helpers`_ and the `report collector`_.

Test Helpers
............

Test helpers implement server side protocols that are of assistance to
ooniprobes when running tests.

If you would like to see a test helper implemented inside of oonib, thats
great!
All you have to do is `open a ticket on trac
<https://trac.torproject.org/projects/tor/newticket?component=Ooni&keywords=oonib_testhelpers%20ooni_wishlist&summary=Add%20support%20for%20PROTOCOL_NAME%20test%20helper>`_.

To get an idea of the current implementation status of test helpers see the
`oonib/testhelpers/
<https://gitweb.torproject.org/ooni-probe.git/tree/HEAD:/oonib/testhelpers>`_
directory of the ooniprobe git repository.

.. TODO
   write up the list of currently implemented test helpers and how to use them.

Report collector
................

.. autoclass:: oonib.report.file_collector.NewReportHandlerFile
    :noindex:


An ooniprobe run
================

Here we describe how an ooniprobe run should look like:

  1. If configured to do so ooniprobe will start a connection to the Tor
       network for the purpose of having a known good test channel and for
       having a way of reporting to the backend collector

  2. It will obtain it's IP Address from Tor via the getinfo addr Tor Ctrl port
       request.

  3. If a collect is specified it will connect to the reporting system and get
       a report id that allows them to submit reports to the collector.

  4. If inputs are specified it will slice them up into chunks of request to be
       performed in parallel.

  5. Once every chunk of inputs (called an InputUnit) will have completed the
       report file and/or the collector will be updated.


ooniprobe API
=============

The goals of the ooniprobe API is that of allowing applications to interact
with an ooniprobe.

Such API will be exposed as an HTTP service that communicates with applications
thanks to JSON formatted messages.

When ooniprobe is launched it will start as a daemon. Through the HTTP based
API it will be possible to `start tests`_, `stop tests`_ and `monitor test
progress`_.

By having it use HTTP it will be possible to decouple the problem of running
tests from that of controlling them.
You can think of it as the Tor Control port of ooniprobe.

The kinds of clients that will be interested in using such API are:

  * The ooniprobe *command line interface*

  * The ooniprobe *HTML5/JS web application*

  * Any *third party* tool that is interested in running ooniprobe tests with
    custom arguments.

Towards a RPC like interface
----------------------------

Such API will allow ooniprobes to expose such API as a Tor Hidden
Service (if the user wishes to do so). This will allow people running ooniprobe
to give the .onion address of the probe to a censorship researcher and they
will then be able to run tests from the network vantage point of the probe.

Draft API specification
------------------------

Through the ooniprobe API it will be possible to `start tests`_, `stop tests`_ and `monitor test
progress`_.

Start tests
...........

.. TODO

Stop tests
...........

.. TODO

Monitor test progress
......................

.. TODO

Implementation status
=====================

.. TODO


