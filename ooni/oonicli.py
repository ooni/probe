import sys
import os
import yaml

from twisted.python import usage
from twisted.python.util import spewer
from twisted.internet import defer

from ooni import errors, __version__

from ooni.settings import config
from ooni.director import Director
from ooni.deck import Deck, nettest_to_path
from ooni.nettest import NetTestLoader

from ooni.utils import log, checkForRoot


class Options(usage.Options):
    synopsis = """%s [options] [path to test].py
    """ % (os.path.basename(sys.argv[0]),)

    longdesc = ("ooniprobe loads and executes a suite or a set of suites of"
                " network tests. These are loaded from modules, packages and"
                " files listed on the command line")

    optFlags = [["help", "h"],
                ["resume", "r"],
                ["no-collector", "n"],
                ["no-geoip", "g"],
                ["list", "s"],
                ["printdeck", "p"],
                ["verbose", "v"]
                ]

    optParameters = [
        ["reportfile", "o", None, "report file name"],
        ["testdeck", "i", None,
         "Specify as input a test deck: a yaml file containing the tests to run and their arguments"],
        ["collector", "c", None,
         "Address of the collector of test results. This option should not be used, but you should always use a bouncer."],
        ["bouncer", "b", 'httpo://nkvphnp3p6agi5qq.onion',
         "Address of the bouncer for test helpers. default: httpo://nkvphnp3p6agi5qq.onion"],
        ["logfile", "l", None, "log file name"],
        ["pcapfile", "O", None, "pcap file name"],
        ["configfile", "f", None,
         "Specify a path to the ooniprobe configuration file"],
        ["datadir", "d", None,
         "Specify a path to the ooniprobe data directory"],
        ["annotations", "a", None,
         "Annotate the report with a key:value[, key:value] format."]]

    compData = usage.Completions(
        extraActions=[usage.CompleteFiles(
            "*.py", descr="file | module | package | TestCase | testMethod",
            repeat=True)],)

    tracer = None

    def __init__(self):
        self['test'] = None
        usage.Options.__init__(self)

    def opt_spew(self):
        """
        Print an insanely verbose log of everything that happens.  Useful
        when debugging freezes or locks in complex code.
        """
        sys.settrace(spewer)

    def opt_version(self):
        """
        Display the ooniprobe version and exit.
        """
        print "ooniprobe version:", __version__
        sys.exit(0)

    def parseArgs(self, *args):
        if self['testdeck'] or self['list']:
            return
        try:
            self['test_file'] = args[0]
            self['subargs'] = args[1:]
        except:
            raise usage.UsageError("No test filename specified!")


def parseOptions():
    print "WARNING: running ooniprobe involves some risk that varies greatly"
    print "         from country to country. You should be aware of this when"
    print "         running the tool. Read more about this in the manpage or README."
    cmd_line_options = Options()
    if len(sys.argv) == 1:
        cmd_line_options.getUsage()
    try:
        cmd_line_options.parseOptions()
    except usage.UsageError as ue:
        print cmd_line_options.getUsage()
        raise SystemExit("%s: %s" % (sys.argv[0], ue))

    return dict(cmd_line_options)


def runWithDirector(logging=True, start_tor=True, check_incoherences=True):
    """
    Instance the director, parse command line options and start an ooniprobe
    test!
    """
    global_options = parseOptions()
    config.global_options = global_options
    config.set_paths()
    config.initialize_ooni_home()
    try:
        config.read_config_file(check_incoherences=check_incoherences)
    except errors.ConfigFileIncoherent:
        sys.exit(6)

    if global_options['verbose']:
        config.advanced.debug = True

    if not start_tor:
        config.advanced.start_tor = False

    if logging:
        log.start(global_options['logfile'])

    if config.privacy.includepcap:
        try:
            checkForRoot()
            from ooni.utils.txscapy import ScapyFactory
            config.scapyFactory = ScapyFactory(config.advanced.interface)
        except errors.InsufficientPrivileges:
            log.err("Insufficient Privileges to capture packets."
                    " See ooniprobe.conf privacy.includepcap")
            sys.exit(2)

    director = Director()
    if global_options['list']:
        print "# Installed nettests"
        for net_test_id, net_test in director.getNetTests().items():
            print "* %s (%s/%s)" % (net_test['name'],
                                    net_test['category'],
                                    net_test['id'])
            print "  %s" % net_test['description']

        sys.exit(0)

    elif global_options['printdeck']:
        del global_options['printdeck']
        print "# Copy and paste the lines below into a test deck to run the specified test with the specified arguments"
        print yaml.safe_dump([{'options': global_options}]).strip()

        sys.exit(0)

    if global_options.get('annotations') is not None:
        annotations = {}
        for annotation in global_options["annotations"].split(","):
            pair = annotation.split(":")
            if len(pair) == 2:
                key = pair[0].strip()
                value = pair[1].strip()
                annotations[key] = value
            else:
                log.err("Invalid annotation: %s" % annotation)
                sys.exit(1)
        global_options["annotations"] = annotations

    if global_options['no-collector']:
        log.msg("Not reporting using a collector")
        global_options['collector'] = None
        start_tor = False
    else:
        start_tor = True

    deck = Deck(no_collector=global_options['no-collector'])
    deck.bouncer = global_options['bouncer']
    if global_options['collector']:
        start_tor |= True

    try:
        if global_options['testdeck']:
            deck.loadDeck(global_options['testdeck'])
        else:
            log.debug("No test deck detected")
            test_file = nettest_to_path(global_options['test_file'], True)
            net_test_loader = NetTestLoader(global_options['subargs'],
                                            test_file=test_file)
            if global_options['collector']:
                net_test_loader.collector = global_options['collector']
            deck.insert(net_test_loader)
    except errors.MissingRequiredOption as option_name:
        log.err('Missing required option: "%s"' % option_name)
        incomplete_net_test_loader = option_name.net_test_loader
        print incomplete_net_test_loader.usageOptions().getUsage()
        sys.exit(2)
    except errors.NetTestNotFound as path:
        log.err('Requested NetTest file not found (%s)' % path)
        sys.exit(3)
    except errors.OONIUsageError as e:
        log.err(e)
        print e.net_test_loader.usageOptions().getUsage()
        sys.exit(4)
    except Exception as e:
        if config.advanced.debug:
            log.exception(e)
        log.err(e)
        sys.exit(5)

    start_tor |= deck.requiresTor
    d = director.start(start_tor=start_tor,
                       check_incoherences=check_incoherences)

    def setup_nettest(_):
        try:
            return deck.setup()
        except errors.UnableToLoadDeckInput as error:
            return defer.failure.Failure(error)

    def director_startup_handled_failures(failure):
        log.err("Could not start the director")
        failure.trap(errors.TorNotRunning,
                     errors.InvalidOONIBCollectorAddress,
                     errors.UnableToLoadDeckInput,
                     errors.CouldNotFindTestHelper,
                     errors.CouldNotFindTestCollector,
                     errors.ProbeIPUnknown,
                     errors.InvalidInputFile,
                     errors.ConfigFileIncoherent)

        if isinstance(failure.value, errors.TorNotRunning):
            log.err("Tor does not appear to be running")
            log.err("Reporting with the collector %s is not possible" %
                    global_options['collector'])
            log.msg(
                "Try with a different collector or disable collector reporting with -n")

        elif isinstance(failure.value, errors.InvalidOONIBCollectorAddress):
            log.err("Invalid format for oonib collector address.")
            log.msg(
                "Should be in the format http://<collector_address>:<port>")
            log.msg("for example: ooniprobe -c httpo://nkvphnp3p6agi5qq.onion")

        elif isinstance(failure.value, errors.UnableToLoadDeckInput):
            log.err("Unable to fetch the required inputs for the test deck.")
            log.msg(
                "Please file a ticket on our issue tracker: https://github.com/thetorproject/ooni-probe/issues")

        elif isinstance(failure.value, errors.CouldNotFindTestHelper):
            log.err("Unable to obtain the required test helpers.")
            log.msg(
                "Try with a different bouncer or check that Tor is running properly.")

        elif isinstance(failure.value, errors.CouldNotFindTestCollector):
            log.err("Could not find a valid collector.")
            log.msg(
                "Try with a different bouncer, specify a collector with -c or disable reporting to a collector with -n.")

        elif isinstance(failure.value, errors.ProbeIPUnknown):
            log.err("Failed to lookup probe IP address.")
            log.msg("Check your internet connection.")

        elif isinstance(failure.value, errors.InvalidInputFile):
            log.err("Invalid input file \"%s\"" % failure.value)

        elif isinstance(failure.value, errors.ConfigFileIncoherent):
            log.err("Incoherent config file")

        if config.advanced.debug:
            log.exception(failure)

    def director_startup_other_failures(failure):
        log.err("An unhandled exception occurred while starting the director!")
        log.exception(failure)

    # Wait until director has started up (including bootstrapping Tor)
    # before adding tests
    def post_director_start(_):
        for net_test_loader in deck.netTestLoaders:
            # Decks can specify different collectors
            # for each net test, so that each NetTest
            # may be paired with a test_helper and its collector
            # However, a user can override this behavior by
            # specifying a collector from the command-line (-c).
            # If a collector is not specified in the deck, or the
            # deck is a singleton, the default collector set in
            # ooniprobe.conf will be used

            collector = None
            if not global_options['no-collector']:
                if global_options['collector']:
                    collector = global_options['collector']
                elif 'collector' in config.reports \
                        and config.reports['collector']:
                    collector = config.reports['collector']
                elif net_test_loader.collector:
                    collector = net_test_loader.collector

            if collector and collector.startswith('httpo:') \
                    and (not (config.tor_state or config.tor.socks_port)):
                raise errors.TorNotRunning

            test_details = net_test_loader.testDetails
            test_details['annotations'] = global_options['annotations']

            director.startNetTest(net_test_loader,
                                  global_options['reportfile'],
                                  collector)
        return director.allTestsDone

    def start():
        d.addCallback(setup_nettest)
        d.addCallback(post_director_start)
        d.addErrback(director_startup_handled_failures)
        d.addErrback(director_startup_other_failures)
        return d

    return start()
