from twisted.internet import protocol, defer, reactor

from ooni.settings import config
from ooni.nettest import NetTestCase
from ooni.utils import log
from ooni.geoip import probe_ip


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

    def cancelTimer(self):
        if self.timeout and self.timer:
            self.timer.cancel()
            self.timer = None

    def close(self, reason=None):
        self.reason = reason
        self.transport.loseConnection()

    def resetTimer(self):
        if self.timeout is not None:
            if self.timer is not None and self.timer.active():
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
        log.debug("STDOUT: %s" % data)
        self.stdout += data
        if self.shouldClose():
            self.close("condition_met")
        self.handleRead(data,  None)

    def errReceived(self, data):
        log.debug("STDERR: %s" % data)
        self.stderr += data
        if self.shouldClose():
            self.close("condition_met")
        self.handleRead(None,  data)


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

    def handleRead(self,  stdout,  stderr=None):
        pass


class ProcessTest(NetTestCase):
    name = "Base Process Test"
    version = "0.1"

    requiresRoot = False
    timeout = 5
    processDirector = None

    def _setUp(self):
        super(ProcessTest, self)._setUp()

    def processEnded(self, result, command):
        log.debug("Finished %s: %s" % (command, result))
        if not isinstance(self.report.get('commands'), list):
            self.report['commands'] = []

        # Attempt to redact the IP address of the probe from the standard output
        if config.privacy.includeip is False and probe_ip.address is not None:
            result['stdout'] = result['stdout'].replace(probe_ip.address, "[REDACTED]")
            result['stderr'] = result['stderr'].replace(probe_ip.address, "[REDACTED]")

        self.report['commands'].append({
            'command_name': ' '.join(command),
            'command_stdout': result['stdout'],
            'command_stderr': result['stderr'],
            'command_exit_reason': result['exit_reason'],
        })
        return result

    def run(self, command, finished=None, env={}, path=None, usePTY=0):
        d = defer.Deferred()
        d.addCallback(self.processEnded, command)
        self.processDirector = ProcessDirector(d, finished, self.timeout)
        self.processDirector.handleRead = self.handleRead
        reactor.spawnProcess(self.processDirector, command[0], command, env=env, path=path, usePTY=usePTY)
        return d

    # handleRead is not an abstract method to be backwards compatible
    def handleRead(self,  stdout,  stderr=None):
        pass
