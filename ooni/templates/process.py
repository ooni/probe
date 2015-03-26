from twisted.internet import protocol, defer, reactor

from ooni.nettest import NetTestCase
from ooni.errors import failureToString
from ooni.utils import log


class ProcessDirector(protocol.ProcessProtocol):
    def __init__(self, d, finished=None):
        self.d = d
        self.stderr = ""
        self.stdout = ""
        self.finished = finished

    def data(self):
        return

    def finish(self, reason=None):
        exit_reason = failureToString(reason)
        data = {
            "stderr": self.stderr,
            "stdout": self.stdout,
            "exit_reason": exit_reason
        }
        self.d.callback(data)

    def shouldClose(self):
        if self.finished is None:
            return False
        return self.finished(self.stdout, self.stderr)

    def connectionMade(self):
        self.transport.write("")
        self.transport.closeStdin()

    def outReceived(self, data):
        log.debug("STDOUT: %s" % data)
        self.stdout += data
        if self.shouldClose():
            self.transport.loseConnection()

    def errReceived(self, data):
        log.debug("STDERR: %s" % data)
        self.stderr += data

    def inConnectionLost(self):
        log.debug("inConnectionLost")
        # self.d.callback(self.data())

    def outConnectionLost(self):
        log.debug("outConnectionLost")

    def errConnectionLost(self):
        log.debug("errConnectionLost")

    def processExited(self, reason):
        log.debug("Exited %s" % reason)

    def processEnded(self, reason):
        log.debug("Ended %s" % reason)
        self.finish(reason)


class ProcessTest(NetTestCase):
    name = "Base Process Test"
    version = "0.1"

    requiresRoot = False
    timeout = 5
    address = None
    port = None

    def _setUp(self):
        super(ProcessTest, self)._setUp()

    def processEnded(self, result):
        self.report.update(result)
        return result

    def run(self, command):
        d = defer.Deferred()
        d.addCallback(self.processEnded)
        processDirector = ProcessDirector(d)
        reactor.spawnProcess(processDirector, command[0], command)
        return d
