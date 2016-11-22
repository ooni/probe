import tempfile
import os
import sys

from twisted.internet import defer, reactor
from twisted.internet.error import ProcessExitedAlready
from twisted.python import usage

from ooni.utils import log, net
from ooni.templates import process, httpt


class UsageOptions(usage.Options):
    optParameters = [
        ['psiphonpath', 'p', None, 'Specify psiphon python client path.'],
        ['url', 'u', net.GOOGLE_HUMANS[0],
            'Specify the URL to fetch over psiphon (default: http://www.google.com/humans.txt).'],
        ['expected-body', 'e', net.GOOGLE_HUMANS[1],
            'Specify the beginning of the expected body in the response (default: ' + net.GOOGLE_HUMANS[1] + ').']
    ]

class PsiphonTest(httpt.HTTPTest,  process.ProcessTest):

    """
    This class tests Psiphon python client

    test_psiphon:
      Starts a Psiphon, check if it bootstraps successfully
      (print a line in stdout).
      Then, perform an HTTP request using the proxy
    """

    name = "Psiphon Test"
    description = ("Bootstraps Psiphon and "
                   "does a HTTP GET for the specified URL.")
    author = "juga"
    version = "0.1.0"
    timeout = 120
    usageOptions = UsageOptions

    def _setUp(self):
        self.localOptions['socksproxy'] = '127.0.0.1:1080'
        super(PsiphonTest, self)._setUp()

    def setUp(self):
        log.debug('PsiphonTest.setUp')

        self.report['bootstrapped_success'] = None
        self.report['request_success'] = None
        self.report['psiphon_found'] = None
        self.report['default_configuration'] = True

        self.bootstrapped = defer.Deferred()
        self.url = self.localOptions['url']

        if self.localOptions['url'] != net.GOOGLE_HUMANS[0]:
            self.report['default_configuration'] = False

        if self.localOptions['expected-body'] != net.GOOGLE_HUMANS[1]:
            self.report['default_configuration'] = False

        if self.localOptions['psiphonpath']:
            self.psiphonpath = self.localOptions['psiphonpath']
        else:
            # Psiphon is not installable and to run it manually, it has to be
            # run from the psiphon directory, so it wouldn't make sense to
            # install it in the PATH. For now, we assume that Psiphon sources
            # are in the user's home directory.
            from os import path, getenv
            self.psiphonpath = path.join(
                getenv('HOME'), 'psiphon-circumvention-system/pyclient/pyclient')
            log.debug('psiphon path: %s' % self.psiphonpath)

    def createCommand(self):
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
        log.debug('command: %s' % ' '.join(self.command))

    def handleRead(self, stdout, stderr):
        if 'Press Ctrl-C to terminate.' in self.processDirector.stdout:
            if not self.bootstrapped.called:
                # here the text 'Press Ctrl-C to terminate.' has been found
                # and it was to call doRequest
                self.report['bootstrapped_success'] = True
                log.debug("PsiphonTest: calling bootstrapped.callback")
                self.bootstrapped.callback(None)

    def test_psiphon(self):
        log.debug('PsiphonTest.test_psiphon')
        self.createCommand()
        if not os.path.exists(self.psiphonpath):
            log.err('psiphon path does not exists, is it installed?')
            self.report['psiphon_found'] = False
            log.debug("Adding %s to report" % self.report)
            # XXX: the original code written by juga0 readed
            #     > return defer.succeed(None)
            # but this caused `ooniprobe -ng` to hang forever, so I
            # rewrote the code to return a deferred and simulate calling
            # its callback method, to trigger an event.
            #     -sbs
            reactor.callLater(0.0, self.bootstrapped.callback, None)
            return self.bootstrapped

        self.report['psiphon_found'] = True
        log.debug("Adding %s to report" % self.report)

        # Using pty to see output lines as soon as they get wrotten in the
        # buffer, otherwise the test might not see lines until the buffer is
        # full with some block size and therefore the test would
        # terminate with error
        finished = self.run(self.command,
                            env=dict(PYTHONPATH=self.psiphonpath),
                            path=self.psiphonpath,
                            usePTY=1)
        # here psiphon command has been run, and if it finds the text
        # 'Press Ctrl-C to terminate' in handleRead it will write to the
        # report self.report['bootstrapped_success'] = True
        self.report['bootstrapped_success'] = False

        def callDoRequest(_):
            log.debug("PsiphonTest.callDoRequest: %r" %(_,))
            d = self.doRequest(self.url)
            def addSuccessToReport(res):
                log.debug("PsiphonTest.callDoRequest.addSuccessToReport")
                if res.body.startswith(self.localOptions['expected-body']):
                    self.report['request_success'] = True
                else:
                    self.report['request_success'] = False

                return res
            d.addCallback(addSuccessToReport)
            def addFailureToReport(res):
                log.debug("PsiphonTest.callDoRequest.addFailureToReport. res=%r" % (res,))
                self.report['request_success'] = False
                return res
            d.addErrback(addFailureToReport)
            return d
        self.bootstrapped.addCallback(callDoRequest)

        def cleanup(_):
            log.debug('PsiphonTest:cleanup')
            try:
                self.processDirector.transport.signalProcess('INT')
            except ProcessExitedAlready:
                pass
            os.remove(self.command[1])
            return finished

        self.bootstrapped.addBoth(cleanup)
        return self.bootstrapped
