from ooni import nettest
from ooni.utils import log
from twisted.internet import defer, protocol, reactor
from twisted.python import usage

import os


def which(program):
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file
    return None


class UsageOptions(usage.Options):
    optParameters = [
        ['interpreter', 'i', '', 'The interpreter to use'],
        ['script', 's', '', 'The script to run']
    ]


class ScriptProcessProtocol(protocol.ProcessProtocol):
    def __init__(self, test_case):
        self.test_case = test_case
        self.deferred = defer.Deferred()

    def connectionMade(self):
        log.debug("connectionMade")
        self.transport.closeStdin()
        self.test_case.report['lua_output'] = ""

    def outReceived(self, data):
        log.debug('outReceived: %s' % data)
        self.test_case.report['lua_output'] += data

    def errReceived(self, data):
        log.err('Script error: %s' % data)
        self.transport.signalProcess('KILL')

    def processEnded(self, status):
        rc = status.value.exitCode
        log.debug('processEnded: %s, %s' % \
                  (rc, self.test_case.report['lua_output']))
        if rc == 0:
            self.deferred.callback(self)
        else:
            self.deferred.errback(rc)


# TODO: Maybe the script requires a back-end.
class Script(nettest.NetTestCase):
    name = "Script test"
    version = "0.1"
    authors = "Dominic Hamon"

    usageOptions = UsageOptions
    requiredOptions = ['interpreter', 'script']
    requiresRoot = False
    requiresTor = False

    def test_run_script(self):
        """
        We run the script specified in the usage options and take whatever
        is printed to stdout as the results of the test.
        """
        processProtocol = ScriptProcessProtocol(self)

        interpreter = self.localOptions['interpreter']
        if not which(interpreter):
            log.err('Unable to find %s executable in PATH.' % interpreter)
            return

        reactor.spawnProcess(processProtocol,
                             interpreter,
                             args=[interpreter, self.localOptions['script']],
                             env={'HOME': os.environ['HOME']},
                             usePTY=True)

        if not reactor.running:
            reactor.run()
        return processProtocol.deferred
