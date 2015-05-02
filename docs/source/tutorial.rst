Tutorial
========

Writing a TCP port scanner
--------------------------

Our goal is to write an OONI test that takes as input a list of ip:port
combinations from a file and attempts to detect which ones are reachable
and open and which ones are not.

Following this tutorial requires basic knowledge of event-driven programming
(specifically 'Twisted')

Creating test
--------------

We base our test on the TCP subclass :class:`ooni.templates.tcpt.TCPTest`,
since it the most suitable for our requirements. We then create the file
'tcp_port_scanner.py' inside 'ooni/nettests/experimental'.

All tests start in the 'experimental' directory, until they are tested
and may then be moved to the stable test folders. 

We start by adding our base class into 'tcp_port_scanner.py'::

    class TCPPortScan(tcpt.TCPTest):

Setup
------

OONI requires some basic information from all tests before running them.
To provide this information we add the following to our test::

    class TCPPortScan(tcpt.TCPTest):
        name = 'TCP_port_scan_test'
        author = 'OONI Contributor <ooni@torproject.org>'
        version = '0.0.1'

        # Some tests may require root access
        requiresRoot = False
        requiresTor  = False

Inputs
------

We need to provide a file to read the IP addresses from. We can do
this by adding::

    class TCPPortScan(tcpt.TCPTest):
        ...
        inputFile = ['file', 'f', None, "Short file description"] 
        requiredOptions = ['file']
        ...

When the test is run, the file will be opened by 
:class:`ooni.nettest.NetTestCase.inputProcessor`. By default the
'inputProcessor' will read line-by-line and feed them to the test.
However, in this test case we may want to skip over the comment lines
that start with a '#'. We override 'inputProcessor'::

     class TCPPortScan(tcpt.TCPTest):
        ...
        def inputProcessor(self, filename):
            fp = open(filename)
            for x in fp.xreadlines():
                if x.startswith("#"):
                    continue
                yield x.strip()
            fp.close()
        ...

Once the test is run, the input may be accessed via 'self.input'.

Writing Tests
-------------

Any functioned prefixed with 'test' will be run by OONI for each
input. We implement the TCP connection test by adding::

    class TCPPortScan(tcpt.TCPTest):
        ...
        def test_tcp_port(self):
            def got_response(response):
                self.report['connection_success'] = True
                print "Connection Successful"

            def connection_failed(failure):
                self.report['connection_success'] = False
                print "Connection Failed"

            self.address = self.input.split(":")[0]
            self.port    = self.input.split(":")[1]
            payload = ""

            d = self.sendPayload(payload)
            d.addErrback(connection_failed)
            d.addCallback(got_response)

            return d

Note that all test functions **must** return a Deferred object.
As shown above, information can add to the OONI report using::

    self.report['something'] = value

Runninng Tests
--------------

If OONI is installed on your computer, you may run the above test
by::

    ooniprobe nettests/experimental/tcp_port_scanner.py -f /path/to/ip_list.txt

By default, this will cause OONI to connect to tor and upload the results
of the test. To save time during development, consider using the '-n' flag, 
temporarily disabling upload. Additionally, the '-v' is also useful,
as OONI by default doesn't print the line if a runtime error occurs::

    ooniprobe -n -v nettests/experimental/tcp_port_scanner.py -f /path/to/ip_list.txt

Reports
-------

Once 'ooniprobe' is invoked, a report will be created in the current working
directory. This report is structed in the YAMLOO format - a format based on
YAML.
