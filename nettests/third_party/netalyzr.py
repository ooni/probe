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

class NetalyzrWrapperTest(nettest.TestCase):
    name = "NetalyzrWrapper"

    def setUp(self):
        cwd = os.path.abspath(os.path.join(os.path.abspath(__file__), '..'))

        # XXX set the output directory to something more uniform
        outputdir = os.path.join(cwd, '..', '..')

        program_path = os.path.join(cwd, 'NetalyzrCLI.jar')
        program = "java -jar %s " % program_path

        test_token = time.asctime(time.gmtime()).replace(" ", "_").strip()

        output_file = os.path.join(outputdir,
                "NetalyzrCLI_" + test_token + ".out")
        output_file.strip()
        self.run_me = program + " 2>&1 >> " + output_file

    def test_run_netalyzr(self):
        """
        This test simply wraps netalyzr and runs it from command line
        """
        log.msg("Running NetalyzrWrapper (this will take some time, be patient)")
        log.debug("with command '%s'" % self.run_me)
        os.system(self.run_me)
        self.report['netalyzr_report'] = self.output_file
        log.debug("finished running NetalzrWrapper")

