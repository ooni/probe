from twisted.internet import defer, reactor
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.web.client import ProxyAgent, readBody
from ooni.templates.process import ProcessTest, ProcessDirector
from ooni.utils import log
from ooni.errors import handleAllFailures, TaskTimedOut
import os.path
from os import getenv


class LanternBootstrapProcessDirector(ProcessDirector):
    """
    This Process Director monitors Lantern during its
    bootstrap and fires a callback if bootstrap is
    successful or an errback if it fails to bootstrap
    before timing out.
    """

    def __init__(self, timeout=None):
        self.stderr = ""
        self.stdout = ""
        self.finished = None
        self.timeout = timeout
        self.stdin = None
        self.timer = None
        self.exit_reason = None
        self.bootstrapped = defer.Deferred()

    def errReceived(self, data):
        self.stderr += data

    def processEnded(self, reason):
        log.debug("Ended %s" % reason)

    def cancelTimer(self):
        if self.timeout and self.timer:
            self.timer.cancel()
            log.debug("Cancelled Timer")

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

    XXX: fix the path issue
    """

    name = "Lantern Circumvention Tool Test"
    author = "Aaron Gibson"
    version = "0.0.1"
    timeout = 20

    def setUp(self):
        self.processDirector = LanternBootstrapProcessDirector(timeout=self.timeout)

    def runLantern(self):
        command = ["lantern_linux", "--headless"]
	paths = filter(os.path.exists,[os.path.join(os.path.expanduser(x), command[0]) for x in getenv('PATH').split(':')])
	if paths:
            command[0] = paths[0]
        log.debug("Spawning Lantern")
        reactor.spawnProcess(self.processDirector, command[0], command)

    def addOutputToReport(self, result):
        self.report['stdout'] = self.processDirector.stdout
        self.report['stderr'] = self.processDirector.stderr
        return result

    def test_lantern_circumvent(self):

        proxyEndpoint=TCP4ClientEndpoint(reactor, '127.0.0.1', 8787)
        agent = ProxyAgent(proxyEndpoint, reactor)

        def addResultToReport(result):
            self.report['body'] = result
            self.report['bootstrapped'] = True

        def addFailureToReport(failure):
            self.report['failure'] = handleAllFailures(failure)
            self.report['bootstrapped'] = False

        def doRequest(noreason):
            log.debug("Doing HTTP request via Lantern (127.0.0.1:8787) for http://google.com")
            request = agent.request("GET", "http://google.com")
            request.addCallback(readBody)
            request.addCallback(addResultToReport)
            return request

        self.processDirector.bootstrapped.addCallback(doRequest)
        self.processDirector.bootstrapped.addBoth(self.addOutputToReport)
        self.processDirector.bootstrapped.addErrback(addFailureToReport)
        self.runLantern()
        return self.processDirector.bootstrapped
