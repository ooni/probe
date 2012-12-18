# -*- encoding: utf-8 -*-
#
# This is a wrapper around the Netalyzer Java command line client
#
# :authors: Jacob Appelbaum <jacob@appelbaum.net>
#           Arturo "hellais" Filastò <art@fuffa.org>
# :licence: see LICENSE

from ooni import nettest
from ooni.utils import log
import time
import os
from twisted.internet import reactor, threads, defer

class NetalyzrWrapperTest(nettest.NetTestCase):
    name = "NetalyzrWrapper"

    def setUp(self):
        cwd = os.path.abspath(os.path.join(os.path.abspath(__file__), '..'))

        # XXX set the output directory to something more uniform
        outputdir = os.path.join(cwd, '..', '..')

        program_path = os.path.join(cwd, 'NetalyzrCLI.jar')
        program = "java -jar %s -d" % program_path

        test_token = time.asctime(time.gmtime()).replace(" ", "_").strip()

        self.output_file = os.path.join(outputdir,
                "NetalyzrCLI_" + test_token + ".out")
        self.output_file.strip()
        self.run_me = program + " 2>&1 >> " + self.output_file

    def blocking_call(self):
        try:
            result = threads.blockingCallFromThread(reactor, os.system, self.run_me) 
        except:
            log.debug("Netalyzr had an error, please see the log file: %s" % self.output_file)
        finally:
            self.clean_up()

    def clean_up(self):
        self.report['netalyzr_report'] = self.output_file
        log.debug("finished running NetalzrWrapper")
        log.debug("Please check %s for Netalyzr output" % self.output_file)

    def test_run_netalyzr(self):
        """
        This test simply wraps netalyzr and runs it from command line
        """
        log.msg("Running NetalyzrWrapper (this will take some time, be patient)")
        log.debug("with command '%s'" % self.run_me)
        # XXX we probably want to use a processprotocol here to obtain the
        # stdout from Netalyzr. This would allows us to visualize progress
        # (currently there is no progress because the stdout of os.system is
        # trapped by twisted) and to include the link to the netalyzr report
        # directly in the OONI report, perhaps even downloading it.
        reactor.callInThread(self.blocking_call)
