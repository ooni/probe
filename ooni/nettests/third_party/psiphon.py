import tempfile
import stat
import os
import sys

from twisted.internet import defer, reactor
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.web.client import readBody
from twisted.python import usage

from txsocksx.http import SOCKS5Agent

from ooni.errors import handleAllFailures, TaskTimedOut
from ooni.utils import log
from ooni.templates import process, httpt
from ooni.templates.process import ProcessTest


class UsageOptions(usage.Options):
    log.debug("UsageOptions")
    optParameters = [
        ['url', 'u', None, 'Specify a single URL to test.'],
        ['psiphonpath', 'p', None, 'Specify psiphon python client path.'],
        ['socksproxy', 's', None, 'Specify psiphon socks proxy ip:port.'],]


class PsiphonTest(httpt.HTTPTest,  process.ProcessTest):

    """
    This class tests Psiphon python client

    test_psiphon:
      Starts a Psiphon, check if it bootstraps successfully
      (print a line in stdout).
      Then, perform an HTTP request using the proxy
    """

    name = "Psiphon Test"
    description = "Bootstraps Psiphon and \
                does a HTTP GET for the specified URL"
    author = "juga"
    version = "0.0.1"
    timeout = 20
    usageOptions = UsageOptions

    def _setUp(self):
        # it is necessary to do this in _setUp instead of setUp
        # because it needs to happen before HTTPTest's _setUp.
        # incidentally, setting this option in setUp results in HTTPTest
        # *saying* it is using this proxy while not actually using it.
        log.debug('PiphonTest._setUp: setting socksproxy')
        self.localOptions['socksproxy'] = '127.0.0.1:1080'
        super(PsiphonTest, self)._setUp()

    def setUp(self):
        log.debug('PsiphonTest.setUp')

        self.bootstrapped = defer.Deferred()
        if self.localOptions['url']:
            self.url = self.localOptions['url']
        else:
            self.url = 'https://check.torproject.org'

        if self.localOptions['psiphonpath']:
            self.psiphonpath = self.localOptions['psiphonpath']
        else:
            # Psiphon is not installable and to run it manually, it has to be
            # run from the psiphon directory, so it wouldn't make sense to
            # install it in the PATH. For now, we assume that Psiphon sources
            # are in the user's home directory.
            from os import path, getenv
            self.psiphonpath = path.join(
                getenv('HOME'), 'psiphon-circumvention-system/pyclient')
            log.debug('psiphon path: %s' % self.psiphonpath)

        # psi_client.py can not be run directly because the paths in the
        # code are relative, so it'll fail to execute from this test
        x = """
from psi_client import connect
connect(False)
"""
        f = tempfile.NamedTemporaryFile(delete=False)
        f.write(x)
        f.close()
        self.command = [sys.executable, f.name]
        log.debug('command: %s' % ''.join(self.command))

    def handleRead(self, stdout, stderr):
        if 'Press Ctrl-C to terminate.' in self.processDirector.stdout:
            if not self.bootstrapped.called:
                log.debug("PsiphonTest: calling bootstrapped.callback")
                self.bootstrapped.callback(None)

    def test_psiphon(self):
        log.debug('PsiphonTest.test_psiphon')

        if not os.path.exists(self.psiphonpath):
            log.err('psiphon path does not exists, is it installed?')
            self.report['success'] = False
            self.report['psiphon_installed'] = False
            log.debug("Adding %s to report" % self.report)
            # XXX: the original code written by juga0 readed
            #     > return defer.succeed(None)
            # but this caused `ooniprobe -ng` to hang forever, so I
            # rewrote the code to return a deferred and simulate calling
            # its callback method, to trigger an event.
            #     -sbs
            reactor.callLater(0.0, self.bootstrapped.callback, None)
            return self.bootstrapped

        self.report['psiphon_installed'] = True
        log.debug("Adding %s to report" % self.report)

        # Using pty to see output lines as soon as they get wrotten in the
        # buffer, otherwise the test might not see lines until the buffer is
        # full with some block size and therefore the test would
        # terminate with error
        finished = self.run(self.command,
                            env=dict(PYTHONPATH=self.psiphonpath),
                            path=self.psiphonpath,
                            usePTY=1)

        def callDoRequest(_):
            return self.doRequest(self.url)
        self.bootstrapped.addCallback(callDoRequest)

        def cleanup(_):
            log.debug('PsiphonTest:cleanup')
            self.processDirector.transport.signalProcess('INT')
            os.remove(self.command[1])
            return finished

        self.bootstrapped.addBoth(cleanup)
        return self.bootstrapped
