from twisted.internet import defer, reactor
from twisted.python import usage
from twisted.web.client import Agent, readBody
from ooni.templates.process import ProcessTest
from ooni.utils import log
from ooni.errors import handleAllFailures, failureToString

import distutils.spawn
import re


class UsageOptions(usage.Options):
    optParameters = [
        ['url', 'u', None, 'Specify a single URL on the OpenVPN subnet to test.'],
        ['openvpn-config', 'c', None, 'Specify an OpenVPN configuration file.'],
    ]


class OpenVPNTest(ProcessTest):

    """
    This class tests OpenVPN connections.

    test_openvpn_circumvent
      Starts an OpenVPN client on Linux and determines
      if it connects successfully to an OpenVPN server.
      Then, it make a HTTP request for http://google.com
      and records the response body or failure string.

    """

    name = "OpenVPN Client Test"
    description = "Connects to an OpenVPN server and does a HTTP GET for the" \
                  "specified URL."
    author = "srvetus "
    version = "0.0.2"
    timeout = 20
    usageOptions = UsageOptions
    requiredOptions = ['url', 'openvpn-config']
    requiresRoot = True

    def setUp(self):
        self.bootstrapped = defer.Deferred()
        self.command = [distutils.spawn.find_executable("openvpn")]
        self.exited = False
        self.url = self.localOptions.get('url')

        if self.localOptions.get('openvpn-config'):
            openvpn_config = self.localOptions.get('openvpn-config')
            self.command.extend(['--config', openvpn_config])

    def stop(self, reason=None):
        """Stop the running OpenVPN process and close the connection"""
        if not self.exited:
            self.processDirector.close()

            # OpenVPN needs to be sent SIGTERM to end cleanly
            self.processDirector.transport.signalProcess('TERM')
            self.exited = True

    def inConnectionLost(self):
            """Monkeypatch inConnectionLost to log failure if the process ends
            unexpectedly before OpenVPN bootstraps.
            """
            log.debug("inConnectionLost")

            if not self.bootstrapped.called:
                self.bootstrapped.errback(Exception("openvpn_exited_unexpectedly"))

    def processExited(self, reason):
            """Monkeypatch processExited to log failure if the process ends
            unexpectedly before OpenVPN bootstraps.
            """
            log.debug("Exited %s" % handleAllFailures(reason))

            # Process exited before OpenVPN bootstrapped. Add failure to report
            # if it is not added already
            if not self.bootstrapped.called:
                self.bootstrapped.errback(Exception("openvpn_exited_unexpectedly"))


    def handleRead(self, stdout=None, stderr=None):
        """handleRead is called with each chunk of data from stdout and stderr

        stdout only contains the latest data chunk, self.processDirector.stdout
        contains the combined stdout data.
        """

        # Read OpenVPN output until bootstrapping succeeds or fails
        if not self.bootstrapped.called:

            # TODO: Determine other OpenVPN messages which indicate connection failure
            if re.search(r'connect to .* failed', self.processDirector.stdout):
                log.debug("OpenVPN connection failed")

                # Bootstrapping failed
                self.bootstrapped.errback(Exception("openvpn_connection_failed"))

            # Check if OpenVPN has bootstrapped and connected successfully
            elif "Initialization Sequence Completed" in self.processDirector.stdout:
                log.debug("OpenVPN connection successful")
                self.processDirector.cancelTimer()
                self.bootstrapped.callback("bootstrapped")

    def test_openvpn_circumvent(self):

        def addResultToReport(result):
            log.debug("request_successful")
            self.report['body'] = result
            self.report['success'] = True

        def addFailureToReport(failure):
            log.debug("Failed: %s" % failureToString(failure))
            self.report['failure'] = failureToString(failure)
            self.report['success'] = False

        def doRequest(noreason):
            """Make a HTTP request over initialized VPN connection"""
            agent = Agent(reactor)

            log.debug("Doing HTTP request to the OpenVPN subnet: %s" % self.url)
            request = agent.request("GET", self.url)
            request.addCallback(readBody)
            request.addCallback(addResultToReport)
            request.addErrback(addFailureToReport)
            return request

        log.debug("Spawning OpenVPN")
        self.d = self.run(self.command)

        # Monkeypatch inConnectionLost and processExited to log when OpenVPN exits early
        self.processDirector.inConnectionLost = self.inConnectionLost
        self.processDirector.processExited = self.processExited

        # Try to make a request when the OpenVPN connection successfully bootstraps
        self.bootstrapped.addCallback(doRequest)

        # Fire failure if OpenVPN connection fails
        self.bootstrapped.addErrback(addFailureToReport)

        # Close OpenVPN after each successful or failed test
        self.bootstrapped.addBoth(self.stop)
        return self.d
