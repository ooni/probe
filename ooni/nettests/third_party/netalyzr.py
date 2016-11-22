# -*- encoding: utf-8 -*-
#
# This is a wrapper around the Netalyzer Java command line client
#
# :authors: Jacob Appelbaum <jacob@appelbaum.net>
#           Arturo "hellais" Filastò <art@fuffa.org>
# :licence: see LICENSE

import time
import os
import distutils.spawn

from twisted.python import usage
from twisted.internet import reactor, threads

from ooni.templates import process
from ooni.utils import log

class JavaNotInstalled(Exception):
    pass

class CouldNotFindNetalyzrCli(Exception):
    pass

class UsageOptions(usage.Options):
    optParameters = [
        ['clipath', 'p', None, 'Specify the path to NetalyzrCLI.jar (can be '
                               'downloaded from '
                               'http://netalyzr.icsi.berkeley.edu/NetalyzrCLI.jar).']
    ]

class NetalyzrWrapperTest(process.ProcessTest):
    name = "NetalyzrWrapper"
    description = "A wrapper around the Netalyzr java command line client."
    author = "Jacob Appelbaum <jacob@appelbaum.net>"

    requiredOptions = ['clipath']

    usageOptions = UsageOptions
    requiresRoot = False
    requiresTor = False

    timeout = 300

    def requirements(self):
        if not distutils.spawn.find_executable("java"):
            raise JavaNotInstalled("Java is not installed.")

    def setUp(self):
        if not os.path.exists(self.localOptions['clipath']):
            raise CouldNotFindNetalyzrCli("Could not find NetalyzrCLI.jar at {}".format(self.localOptions['clipath']))

        self.command = [
            distutils.spawn.find_executable("java"),
            "-jar",
            "{}".format(self.localOptions['clipath']),
            "-d"
        ]

    def test_run_netalyzr(self):
        """
        This test simply wraps netalyzr and runs it from command line
        """
        log.msg("Running NetalyzrWrapper (this will take some time, be patient)")
        log.debug("with command '%s'" % self.command)
        self.d = self.run(self.command, env=os.environ, usePTY=1)
        return self.d
