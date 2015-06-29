from twisted.internet import defer, reactor
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.python import usage
from twisted.web.client import ProxyAgent, readBody
from ooni.templates.process import ProcessTest, ProcessDirector
from ooni.utils import log
from ooni.errors import handleAllFailures, TaskTimedOut
import os.path
from os import getenv

class UsageOptions(usage.Options):
    optParameters = [
        ['url', 'u', None, 'Specify a single URL to test.'],]

class LanternProcessDirector(ProcessDirector):
    """
    This Process Director monitors Lantern during its
    bootstrap and fires a callback if bootstrap is
    successful or an errback if it fails to bootstrap
    before timing out.
    """

    def __init__(self, d, timeout=None):
        self.d = d
        self.stderr = ""
        self.stdout = ""
        self.finished = None
        self.timeout = timeout
        self.stdin = None
        self.timer = None
        self.exit_reason = None
        self.bootstrapped = defer.Deferred()

    def outReceived(self, data):
        self.stdout += data
        # output received, see if we have bootstrapped
        if not self.bootstrapped.called and "client (http) proxy at" in self.stdout:
            log.debug("Bootstrap Detected")
            self.cancelTimer()
            self.bootstrapped.callback("bootstrapped")


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
    description = "Bootstraps Lantern and does a HTTP GET for the specified URL"
    author = "Aaron Gibson"
    version = "0.0.1"
    timeout = 20
    usageOptions = UsageOptions
    requiredOptions = ['url']

    def setUp(self):
        self.command = ["lantern_linux", "--headless"]
        self.d = defer.Deferred()
        self.processDirector = LanternProcessDirector(self.d, timeout=self.timeout)
        self.d.addCallback(self.processEnded, self.command)
        if self.localOptions['url']:
            self.url = self.localOptions['url']

    def runLantern(self):
        paths = filter(os.path.exists,[os.path.join(os.path.expanduser(x), self.command[0]) for x in getenv('PATH').split(':')])
        log.debug("Spawning Lantern")
        reactor.spawnProcess(self.processDirector, paths[0], self.command)

    def test_lantern_circumvent(self):
        proxyEndpoint=TCP4ClientEndpoint(reactor, '127.0.0.1', 8787)
        agent = ProxyAgent(proxyEndpoint, reactor)

        def addResultToReport(result):
            self.report['body'] = result
            self.report['success'] = True

        def addFailureToReport(failure):
            self.report['failure'] = handleAllFailures(failure)
            self.report['success'] = False

        def doRequest(noreason):
            log.debug("Doing HTTP request via Lantern (127.0.0.1:8787) for %s" % self.url)
            request = agent.request("GET", self.url)
            request.addCallback(readBody)
            request.addCallback(addResultToReport)
            request.addCallback(self.processDirector.close)
            return request

        self.processDirector.bootstrapped.addCallback(doRequest)
        self.processDirector.bootstrapped.addErrback(addFailureToReport)
        self.runLantern()
        return self.d
