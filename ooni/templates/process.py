from twisted.internet import protocol, defer, reactor

from ooni.nettest import NetTestCase
from ooni.utils import log


class ProcessDirector(protocol.ProcessProtocol):
    def __init__(self, d, finished=None, timeout=None, stdin=None):
        self.d = d
        self.stderr = ""
        self.stdout = ""
        self.finished = finished
        self.timeout = timeout
        self.stdin = stdin

        self.timer = None
        self.exit_reason = None

    def close(self, reason=None):
        self.reason = reason
        self.transport.loseConnection()

    def resetTimer(self):
        log.debug("Resetting Timer")
        if self.timeout is not None:
            if self.timer is not None:
                self.timer.cancel()
            self.timer = reactor.callLater(self.timeout,
                                           self.close,
                                           "timeout_reached")

    def finish(self, exit_reason=None):
        if not self.exit_reason:
            self.exit_reason = exit_reason
        data = {
            "stderr": self.stderr,
            "stdout": self.stdout,
            "exit_reason": self.exit_reason
        }
        self.d.callback(data)

    def shouldClose(self):
        if self.finished is None:
            return False
        return self.finished(self.stdout, self.stderr)

    def connectionMade(self):
        self.resetTimer()
        if self.stdin is not None:
            self.transport.write(self.stin)
            self.transport.closeStdin()

    def outReceived(self, data):
        self.resetTimer()
        log.debug("STDOUT: %s" % data)
        self.stdout += data
        if self.shouldClose():
            self.close("condition_met")

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
        self.finish("process_done")


class ProcessTest(NetTestCase):
    name = "Base Process Test"
    version = "0.1"

    requiresRoot = False
    timeout = 5

    def _setUp(self):
        super(ProcessTest, self)._setUp()

    def processEnded(self, result, command):
        log.debug("Finished %s: %s" % (command, result))
        key = ' '.join(command)
        self.report[key] = {
            'stdout': result['stdout'],
            'stderr': result['stderr'],
            'exit_reason': result['exit_reason']
        }
        return result

    def run(self, command, finished=None):
        d = defer.Deferred()
        d.addCallback(self.processEnded, command)
        processDirector = ProcessDirector(d, finished, self.timeout)
        reactor.spawnProcess(processDirector, command[0], command)
        return d
