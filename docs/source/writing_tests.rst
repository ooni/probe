Writing OONI tests
==================


The OONI testing API is heavily influenced and partially based on the python
:class:`unittest` module and :class:`twsted.trial`.


Test Cases
----------

The atom of OONI Testing is called a Test Case. A test case class may contain
multiple Test Methods.

.. autoclass:: ooni.nettest.NetTestCase
    :noindex:


If the test you plan to write is not listed on the `Tor OONI trac page
<https://trac.torproject.org/projects/tor/wiki/doc/OONI/Tests>`_, you should
add it to the list and then add a description about it following the `Test
Template <https://gitweb.torproject.org/ooni-probe.git/blob/HEAD:/docs/source/tests/template.rst>`_

Tests are driven by inputs. For every input a new test instance is created,
internally the _setUp method is called that is defined inside of test
templates, then the setUp method that is overwritable by users.

Inputs
------

Inputs are what is given as input to every iteration of the Test Case. You have
100 inputs, then every test case will be run 100 times.

To configure a static set of inputs you should define the
:class:`ooni.nettest.TestCase` attribute ``inputs``. The test will be run
``len(inputs)`` times. Any iterable object is a valid ``inputs`` attribute.

If you would like to have inputs be determined from a user specified input
file, then you must set the ``inputFile`` attribute. This is an array that
specifies what command line option may be used to control this value.

By default the ``inputProcessor`` is set to read the file line by line and
strip newline characters. To change this behavior you must set the
``inputProcessor`` attribute to a function that takes as argument a file
descriptor and yield the next item. The default ``inputProcessor`` looks like
this::


    def lineByLine(filename):
        fp = open(filename)
        for x in fp.xreadlines():
            yield x.strip()
        fp.close()


Setup and command line passing
------------------------------

Tests may define the `setUp` method that will be called every time the Test
Case object is instantiated, in here you may place some common logic to all your
Test Methods that should be run before any testing occurs.

Command line arguments can be parsed thanks to the twisted
`twisted.python.usage.UsageOptions` class.

You will have to subclass this and define the NetTestCase attribute
usageOptions to point to a subclass of this.

::

  class UsageOptions(usage.Options):
    optParameters = [['backend', 'b', 'http://127.0.0.1:57001', 
                        'URL of the test backend to use']
                    ]

  class MyTestCase(nettest.TestCase):
    usageOptions = UsageOptions

    inputFile = ['file', 'f', None, "Some foo file"]
    requiredOptions = ['backend']

    def test_my_test(self):
      self.localOptions['backend']


You will then be able to access the parsed command line arguments via the class
attribute localOptions.

The `requiredOptions` attributes specifies an array of parameters that are
required for the test to run properly.

`inputFile` is a special class attribute that will be used for processing of
the inputFile. The filename that is read here will be given to the
`ooni.nettest.NetTestCase.inputProcessor` method that will yield, by default,
one line of the file at a time.



Test Methods
------------

These shall be defined inside of your :class:`ooni.nettest.TestCase` subclass.
These will be class methods.

All class methods that are prefixed with test\_ shall be run. Functions that
are relevant to your test should be all lowercase separated by underscore.

To add data to the test report you may write directly to the report object like
so::

    def test_my_function():
        result = do_something()
        self.report['something'] = result


OONI will then handle the writing of the data to the final test report.

To access the current input you can use the ``input`` attribute, for example::

    def test_with_input():
        do_something_with_input(self.input)

This will at each iteration over the list of inputs do something with the
input.

Test Templates
--------------

Test templates assist you in writing tests. They already contain all the common
functionality that is useful to running a test of that type. They also take
care of writing the data they collect that is relevant to the test run to the
report file.

Currently implemented test templates are `ooni.templates.scapt` for tests based
on Scapy, `ooni.templates.tcpt` for tests based on TCP, `ooni.templates.httpt`
for tests based on HTTP, `ooni.templates.dnst` for tests based on DNS.


Scapy based tests
.................

Scapy based tests will be a subclass of `ooni.templates.scapyt.BaseScapyTest`.

It provides a wrapper around the scapy send and receive function that will
write the sent and received packets to the report with sanitization of the src
and destination IP addresses.

It has the same syntax as the Scapy sr function, except that it will return a
deferred.

To implement a simple ICMP ping based on this function you can do like so
(taken from nettest/examples/example_scapyt.py):


::

  from twisted.python import usage

  from scapy.all import IP, ICMP

  from ooni.templates import scapyt

  class UsageOptions(usage.Options):
      optParameters = [['target', 't', '8.8.8.8', "Specify the target to ping"]]

  class ExampleICMPPingScapy(scapyt.BaseScapyTest):
      name = "Example ICMP Ping Test"

      usageOptions = UsageOptions

      def test_icmp_ping(self):
          def finished(packets):
              print packets
              answered, unanswered = packets
              for snd, rcv in answered:
                  rcv.show()

          packets = IP(dst=self.localOptions['target'])/ICMP()
          d = self.sr(packets)
          d.addCallback(finished)
          return d

The arguments taken by self.sr() are exactly the same as the scapy send and
receive function, the only difference is that instead of using the regular
scapy super socket it uses our twisted driven wrapper around it.

Alternatively this test can also be written using the
`twisted.defer.inlineCallbacks` decorator, that makes it look more similar to
regular sequential code.

::

  from twisted.python import usage
  from twisted.internet import defer

  from scapy.all import IP, ICMP

  from ooni.templates import scapyt

  class UsageOptions(usage.Options):
      optParameters = [['target', 't', self.localOptions['target'], "Specify the target to ping"]]

  class ExampleICMPPingScapyYield(scapyt.BaseScapyTest):
      name = "Example ICMP Ping Test"

      usageOptions = UsageOptions

      @defer.inlineCallbacks
      def test_icmp_ping(self):
          packets = IP(dst=self.localOptions['target'])/ICMP()
          answered, unanswered = yield self.sr(packets)
          for snd, rcv in answered:
              rcv.show()


Report Format
*************


::

  ###########################################
  # OONI Probe Report for Example ICMP Ping Test test
  # Thu Nov 22 18:20:43 2012
  ###########################################
  ---
  {probe_asn: null, probe_cc: null, probe_ip: 127.0.0.1, software_name: ooniprobe, software_version: 0.0.7.1-alpha,
    start_time: 1353601243.0, test_name: Example ICMP Ping Test, test_version: 0.1}
  ...
  ---
  input: null
  report:
    answer_flags: [ipsrc]
    answered_packets:
    - - raw_packet: !!binary |
          RQAAHAEdAAAuAbjKCAgICH8AAAEAAAAAAAAAAA==
        summary: IP / ICMP 8.8.8.8 > 127.0.0.1 echo-reply 0
    sent_packets:
    - - raw_packet: !!binary |
          RQAAHAABAABAAevPfwAAAQgICAgIAPf/AAAAAA==
        summary: IP / ICMP 127.0.0.1 > 8.8.8.8 echo-request 0
  test_name: test_icmp_ping
  test_started: 1353604843.553605
  ...


TCP based tests
...............

TCP based tests will subclass `ooni.templates.tcpt.TCPTest`.

This test template facilitates the sending of TCP payloads to the wire and
recording the response.

::

  from twisted.internet.error import ConnectionRefusedError
  from ooni.utils import log
  from ooni.templates import tcpt

  class ExampleTCPT(tcpt.TCPTest):
      def test_hello_world(self):
          def got_response(response):
              print "Got this data %s" % response

          def connection_failed(failure):
              failure.trap(ConnectionRefusedError)
              print "Connection Refused"

          self.address = "127.0.0.1"
          self.port = 57002
          payload = "Hello World!\n\r"
          d = self.sendPayload(payload)
          d.addErrback(connection_failed)
          d.addCallback(got_response)
          return d


The possible failures for a TCP connection are:

`twisted.internet.error.NoRouteError` that corresponds to errno.ENETUNREACH

`twisted.internet.error.ConnectionRefusedError` that corresponds to
errno.ECONNREFUSED

`twisted.internet.error.TCPTimedOutError` that corresponds to errno.ETIMEDOUT

Report format
*************

The basic report of a TCP test looks like the following (this is an report
generated by running the above example against a TCP echo server).

::

  ###########################################
  # OONI Probe Report for Base TCP Test test
  # Thu Nov 22 18:18:28 2012
  ###########################################
  ---
  {probe_asn: null, probe_cc: null, probe_ip: 127.0.0.1, software_name: ooniprobe, software_version: 0.0.7.1-alpha,
    start_time: 1353601108.0, test_name: Base TCP Test, test_version: '0.1'}
  ...
  ---
  input: null
  report:
    errors: []
    received: ["Hello World!\n\r"]
    sent: ["Hello World!\n\r"]
  test_name: test_hello_world
  test_started: 1353604708.705081
  ...


TODO finish this with more details

HTTP based tests
................

see nettests/examples/example_httpt.py

TODO

DNS based tests
...............

see nettests/core/dnstamper.py

TODO

