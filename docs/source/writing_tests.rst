Writing OONI tests
==================


The OONI testing API is heavily influenced and partially based on the python
:mod:`unittest` module and :mod:`twisted.trial`.


Test Cases
----------

The atom of OONI Testing is called a Test Case. A test case class may contain
multiple Test Methods.

.. autoclass:: ooni.nettest.NetTestCase
    :noindex:


If the test you plan to write is not listed on the `Tor OONI trac page
<https://trac.torproject.org/projects/tor/wiki/doc/OONI/Tests>`_, you should
add it to the list and then add a description about it following the `test
template <https://gitweb.torproject.org/ooni-probe.git/plain/docs/source/tests/template.rst>`_.

Tests are driven by inputs. For every input a new test instance is created,
internally the _setUp method is called that is defined inside of test
templates, then the setUp method that is overwritable by users.

Gotchas:
**never** call reactor.start of reactor.stop inside of your test method and all
will be good.

Inputs
------

Inputs are what is given as input to every iteration of the Test Case.
If you have 100 inputs, then every test case will be run 100 times.

To configure a static set of inputs you should define the
:class:`ooni.nettest.NetTestCase` attribute ``inputs``. The test will be
run ``len(inputs)`` times. Any iterable object is a valid ``inputs``
attribute.

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

For example, if you wanted to modify inputProcessor to read enteries from a CSV file, you could use::
            
    def inputProcessor(self, filename):
        with open(filename) as csvFile:
            reader = DictReader(csvFile)
            for entry in reader:
                yield entry

Setup and command line passing
------------------------------

Tests may define the `setUp` method that will be called every time the
Test Case object is instantiated, in here you may place some common logic
to all your Test Methods that should be run before any testing occurs.

Command line arguments can be parsed thanks to the twisted
:class:`twisted.python.usage.UsageOptions` class.

You will have to subclass this and define the NetTestCase attribute
usageOptions to point to a subclass of this.

::

  class UsageOptions(usage.Options):
    optParameters = [['backend', 'b', 'http://127.0.0.1:57001', 
                        'URL of the test backend to use']
                    ]

  class MyTestCase(nettest.NetTestCase):
    usageOptions = UsageOptions

    inputFile = ['file', 'f', None, "Some foo file"]
    requiredOptions = ['backend']

    def test_my_test(self):
      self.localOptions['backend']


You will then be able to access the parsed command line arguments via the
class attribute localOptions.

The `requiredOptions` attributes specifies an array of parameters that are
required for the test to run properly.

`inputFile` is a special class attribute that will be used for processing
of the inputFile. The filename that is read here will be given to the
:class:`ooni.nettest.NetTestCase.inputProcessor` method that will yield, by
default, one line of the file at a time.



Test Methods
------------

These shall be defined inside of your :class:`ooni.nettest.NetTestCase`
subclass.  These will be class methods.

All class methods that are prefixed with test\_ shall be run. Functions
that are relevant to your test should be all lowercase separated by
underscore.

To add data to the test report you may write directly to the report object
like so::

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

Test templates assist you in writing tests. They already contain all the
common functionality that is useful to running a test of that type. They
also take care of writing the data they collect that is relevant to the
test run to the report file.

Currently implemented test templates are :mod:`ooni.templates.scapyt` for
tests based on Scapy, :mod:`ooni.templates.tcpt` for tests based on TCP,
:mod:`ooni.templates.httpt` for tests based on HTTP, and
:mod:`ooni.templates.dnst` for tests based on DNS.


Scapy based tests
.................

Scapy based tests will be a subclass of :class:`ooni.templates.scapyt.BaseScapyTest`.

It provides a wrapper around the scapy send and receive function that will
write the sent and received packets to the report with sanitization of the
src and destination IP addresses.

It has the same syntax as the Scapy sr function, except that it will
return a deferred.

To implement a simple ICMP ping based on this function you can do like so
(Taken from :class:`nettest.examples.example_scapyt.ExampleICMPPingScapy`)


::

  from twisted.python import usage

  from scapy.all import IP, ICMP

  from ooni.templates import scapyt

  class UsageOptions(usage.Options):
      optParameters = [['target', 't', '127.0.0.1', "Specify the target to ping"]]

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
:func:`twisted.defer.inlineCallbacks` decorator, that makes it look more similar to
regular sequential code.

::

  from twisted.python import usage
  from twisted.internet import defer

  from scapy.all import IP, ICMP

  from ooni.templates import scapyt

  class UsageOptions(usage.Options):
      optParameters = [['target', 't', '127.0.0.1', "Specify the target to ping"]]

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

TCP based tests will subclass :class:`ooni.templates.tcpt.TCPTest`.

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

:class:`twisted.internet.error.NoRouteError` that corresponds to errno.ENETUNREACH

:class:`twisted.internet.error.ConnectionRefusedError` that corresponds to
errno.ECONNREFUSED

:class:`twisted.internet.error.TCPTimedOutError` that corresponds to errno.ETIMEDOUT

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

HTTP based tests will be a subclass of  :class:`ooni.templates.httpt.HTTPTest`.

It provides methods :func:`ooni.templates.httpt.HTTPTest.processResponseBody` and
:func:`ooni.templates.httpt.HTTPTest.processResponseHeaders` for interacting with the
response body and headers respectively.

For example, to implement a HTTP test that returns the sha256 hash of the
response body (based on :mod:`nettests.examples.example_httpt`):

::

  from ooni.utils import log
  from ooni.templates import httpt
  from hashlib import sha256
  
  class SHA256HTTPBodyTest(httpt.HTTPTest):
      name = "ChecksumHTTPBodyTest"
      author = "Aaron Gibson"
      version = 0.1
  
      inputFile = ['url file', 'f', None,
              'List of URLS to perform GET requests to']
      requiredOptions = ['url file']
  
      def test_http(self):
          if self.input:
              url = self.input
              return self.doRequest(url)
          else:
              raise Exception("No input specified")
  
      def processResponseBody(self, body):
          body_sha256sum = sha256(body).hexdigest()
          self.report['checksum'] = body_sha256sum

Report format
*************

::

  ###########################################
  # OONI Probe Report for ChecksumHTTPBodyTest test
  # Thu Dec  6 17:31:57 2012
  ###########################################
  ---
  options:
    collector: null
    help: 0
    logfile: null
    pcapfile: null
    reportfile: null
    resume: 0
    subargs: [-f, hosts]
    test: nettests/examples/example_http_checksum.py
  probe_asn: null
  probe_cc: null
  probe_ip: 127.0.0.1
  software_name: ooniprobe
  software_version: 0.0.7.1-alpha
  start_time: 1354786317.0
  test_name: ChecksumHTTPBodyTest
  test_version: 0.1
  ...
  ---
  input: http://www.google.com
  report:
    agent: agent
    checksum: d630fa2efd547d3656e349e96ff7af5496889dad959e8e29212af1ff843e7aa1
    requests:
    - request:
        body: null
        headers:
        - - User-Agent
          - - [Opera/9.00 (Windows NT 5.1; U; en), 'Opera 9.0, Windows XP']
        method: GET
        url: http://www.google.com
      response:
        body: '<!doctype html><html ... snip ...  </html>'
        code: 200
        headers:
        - - X-XSS-Protection
          - [1; mode=block]
        - - Set-Cookie
          - ['PREF=ID=fada4216eb3684f9:FF=0:TM=1354800717:LM=1354800717:S=IT-2GCkNAocyXlVa;
              expires=Sat, 06-Dec-2014 13:31:57 GMT; path=/; domain=.google.com', 'NID=66=KWaLbNQumuGuYf0HrWlGm54u9l-DKJwhFCMQXfhQPZM-qniRhmF6QRGXUKXb_8CIUuCOHnyoC5oAX5jWNrsfk-LLJLW530UiMp6hemTtDMh_e6GSiEB4GR3yOP_E0TCN;
              expires=Fri, 07-Jun-2013 13:31:57 GMT; path=/; domain=.google.com; HttpOnly']
        - - Expires
          - ['-1']
        - - Server
          - [gws]
        - - Connection
          - [close]
        - - Cache-Control
          - ['private, max-age=0']
        - - Date
          - ['Thu, 06 Dec 2012 13:31:57 GMT']
        - - P3P
          - ['CP="This is not a P3P policy! See http://www.google.com/support/accounts/bin/answer.py?hl=en&answer=151657
              for more info."']
        - - Content-Type
          - [text/html; charset=UTF-8]
        - - X-Frame-Options
          - [SAMEORIGIN]
    socksproxy: null
  test_name: test_http
  test_runtime: 0.08298492431640625
  test_started: 1354800717.478403
  ...
 

DNS based tests
...............

DNS based tests will be a subclass of :class:`ooni.templates.dnst.DNSTest`.

It provides methods :func:`ooni.templates.dnst.DNSTest.performPTRLookup`
and :func:`ooni.templates.dnst.DNSTest.performALookup`

For example (taken from :mod:`nettests.examples.example_dnst`):

::

  from ooni.templates.dnst import DNSTest
  
  class ExampleDNSTest(DNSTest):
      def test_a_lookup(self):
          def gotResult(result):
              # Result is an array containing all the A record lookup results
              print result
  
          d = self.performALookup('torproject.org', ('8.8.8.8', 53))
          d.addCallback(gotResult)
          return d

Report format
*************

::

  ###########################################
  # OONI Probe Report for Base DNS Test test
  # Thu Dec  6 17:42:51 2012
  ###########################################
  ---
  options:
    collector: null
    help: 0
    logfile: null
    pcapfile: null
    reportfile: null
    resume: 0
    subargs: []
    test: nettests/examples/example_dnst.py
  probe_asn: null
  probe_cc: null
  probe_ip: 127.0.0.1
  software_name: ooniprobe
  software_version: 0.0.7.1-alpha
  start_time: 1354786971.0
  test_name: Base DNS Test
  test_version: 0.1
  ...
  ---
  input: null
  report:
    queries:
    - addrs: [82.195.75.101, 86.59.30.40, 38.229.72.14, 38.229.72.16]
      answers:
      - [<RR name=torproject.org type=A class=IN ttl=782s auth=False>, <A address=82.195.75.101
          ttl=782>]
      - [<RR name=torproject.org type=A class=IN ttl=782s auth=False>, <A address=86.59.30.40
          ttl=782>]
      - [<RR name=torproject.org type=A class=IN ttl=782s auth=False>, <A address=38.229.72.14
          ttl=782>]
      - [<RR name=torproject.org type=A class=IN ttl=782s auth=False>, <A address=38.229.72.16
          ttl=782>]
      query: '[Query(''torproject.org'', 1, 1)]'
      query_type: A
      resolver: [8.8.8.8, 53]
  test_name: test_a_lookup
  test_runtime: 0.028924942016601562
  test_started: 1354801371.980114
  ...

For a more complex example, see: :mod:`nettests.blocking.dnsconsistency`
