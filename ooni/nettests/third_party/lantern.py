import os
import distutils.spawn

from twisted.internet import defer, reactor
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.web.client import ProxyAgent, readBody
from twisted.python import usage

from ooni.templates.process import ProcessTest, ProcessDirector
from ooni.utils import log, net
from ooni.errors import handleAllFailures

class LanternNotInstalled(Exception):
    pass

class UsageOptions(usage.Options):
    optParameters = [
        ['url', 'u', net.GOOGLE_HUMANS[0],
            'Specify the URL to fetch over lantern (default: http://www.google.com/humans.txt).'],
        ['expected-body', 'e', net.GOOGLE_HUMANS[1],
            'Specify the beginning of the expected body in the response (default: ' + net.GOOGLE_HUMANS[1] + ').']
    ]

class LanternTest(ProcessTest):
    """
    This class tests Lantern (https://getlantern.org).

    test_lantern_circumvent
      Starts Lantern on Linux in --headless mode and
      determine if it bootstraps successfully or not.
      Then, make a HTTP request for http://google.com
      and records the response body or failure string.

    """

    name = "Lantern Circumvention Tool Test"
    description = "Bootstraps Lantern, connects to a URL and verifies if it "\
                  "contains the expected input."
    author = "Aaron Gibson"
    version = "0.1.0"
    timeout = 120
    usageOptions = UsageOptions

    def requirements(self):
        if not distutils.spawn.find_executable("lantern"):
            raise LanternNotInstalled('lantern is not installed')

    def setUp(self):
        self.report['body'] = None
        self.report['failure'] = None
        self.report['success'] = None
        self.report['default_configuration'] = True

        self.command = [distutils.spawn.find_executable("lantern"), "--headless"]
        self.bootstrapped = defer.Deferred()
        self.exited = False

        self.url = self.localOptions['url']
        if self.url != net.GOOGLE_HUMANS[0]:
            self.report['default_configuration'] = False

        if self.localOptions['expected-body'] != net.GOOGLE_HUMANS[1]:
            self.report['default_configuration'] = False

    def stop(self, reason=None):
        if not self.exited:
            self.processDirector.close()
            self.processDirector.transport.signalProcess('TERM')
            self.exited = True

    def handleRead(self, stdout=None, stderr=None):
        """
        This is called with each chunk of data from stdout and stderr.
        """
        if not self.bootstrapped.called and "Successfully dialed via" in self.processDirector.stdout:
            log.msg("Lantern connection successful")
            self.processDirector.cancelTimer()
            self.bootstrapped.callback("bootstrapped")

    def test_lantern_circumvent(self):
        def addResultToReport(result):
            self.report['body'] = result
            if result.startswith(self.localOptions['expected-body']):
                log.msg("Got the HTTP response body I expected!")
                self.report['success'] = True
            else:
                self.report['success'] = False

        def addFailureToReport(failure):
            log.err("Failed to connect to lantern")
            log.failure(failure)
            self.report['failure'] = handleAllFailures(failure)
            self.report['success'] = False

        def doRequest(noreason):
            proxyEndpoint = TCP4ClientEndpoint(reactor, '127.0.0.1', 8787)
            agent = ProxyAgent(proxyEndpoint, reactor)
            log.msg("Doing HTTP request via Lantern (127.0.0.1:8787) for %s" % self.url)
            request = agent.request("GET", self.url)
            request.addCallback(readBody)
            request.addCallback(addResultToReport)
            request.addCallback(self.processDirector.close)
            return request

        self.bootstrapped.addCallback(doRequest)
        self.bootstrapped.addErrback(addFailureToReport)
        self.bootstrapped.addBoth(self.stop)
        self.d = self.run(self.command, env=os.environ, usePTY=1)
        return self.d
