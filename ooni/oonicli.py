import sys

import os
import json
import yaml
import random
import urlparse

from twisted.python import usage
from twisted.python.util import spewer
from twisted.internet import defer, reactor, protocol

from ooni import errors, __version__

from ooni.settings import config
from ooni.director import Director
from ooni.deck import Deck, nettest_to_path
from ooni.nettest import NetTestLoader

from ooni.utils import log
from ooni.utils.net import hasRawSocketPermission

from scapy.all import conf



class LifetimeExceeded(Exception): pass

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
         "Address of the bouncer for test helpers."],
        ["logfile", "l", None, "log file name"],
        ["pcapfile", "O", None, "pcap file name"],
        ["configfile", "f", None,
         "Specify a path to the ooniprobe configuration file"],
        ["datadir", "d", None,
         "Specify a path to the ooniprobe data directory"],
        ["annotations", "a", None,
         "Annotate the report with a key:value[, key:value] format."],
        ["queue", "Q", None, "AMQP Queue URL amqp://user:pass@host:port/vhost/queue"]]

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
        log.err("Reporting with a collector is not possible")
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

def setupGlobalOptions(logging, start_tor, check_incoherences):
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
        if hasRawSocketPermission():
            from ooni.utils.txscapy import ScapyFactory
            config.snifferFactory = ScapyFactory(config.advanced.interface, super_socket=conf.L2listen())
        else:
            log.err("Insufficient Privileges to capture packets."
                    " See ooniprobe.conf privacy.includepcap")
            sys.exit(2)
    return global_options

def setupAnnotations(global_options):
    annotations={}
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
    return annotations

def setupCollector(global_options, net_test_loader):
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
    return collector


def createDeck(global_options, url=None):
    log.msg("Creating deck for: %s" % (url))

    deck = Deck(no_collector=global_options['no-collector'])
    deck.bouncer = global_options['bouncer']

    try:
        if global_options['testdeck']:
            deck.loadDeck(global_options['testdeck'])
        else:
            log.debug("No test deck detected")
            test_file = nettest_to_path(global_options['test_file'], True)
            if url is not None:
                args = ('-u', url)
            else:
                args = tuple()
            if any(global_options['subargs']):
                args = global_options['subargs'] + args
            net_test_loader = NetTestLoader(args,
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
    except errors.HTTPSCollectorUnsupported:
        log.err("HTTPS collectors require a twisted version of at least 14.0.2.")
        sys.exit(6)
    except errors.InsecureCollector:
        log.err("Attempting to report to an insecure collector.")
        log.err("To enable reporting to insecure collector set the "
                "advanced->insecure_collector option to true in "
                "your ooniprobe.conf file.")
        sys.exit(7)
    except Exception as e:
        if config.advanced.debug:
            log.exception(e)
        log.err(e)
        sys.exit(5)

    return deck


def runTestWithDirector(director, global_options, url=None,
                        start_tor=True, check_incoherences=True):
    deck = createDeck(global_options, url=url)

    start_tor |= deck.requiresTor

    d = director.start(start_tor=start_tor,
                       check_incoherences=check_incoherences)

    def setup_nettest(_):
        try:
            return deck.setup()
        except errors.UnableToLoadDeckInput as error:
            return defer.failure.Failure(error)


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

            collector = setupCollector(global_options, net_test_loader)

            if collector and collector.startswith('httpo:') \
                    and (not (config.tor_state or config.tor.socks_port)):
                raise errors.TorNotRunning

            net_test_loader.annotations = global_options['annotations']

            director.startNetTest(net_test_loader,
                                    global_options['reportfile'],
                                    collector)
        return director.allTestsDone

    d.addCallback(setup_nettest)
    d.addCallback(post_director_start)
    d.addErrback(director_startup_handled_failures)
    d.addErrback(director_startup_other_failures)
    return d

def runWithDirector(logging=True, start_tor=True, check_incoherences=True):
    """
    Instance the director, parse command line options and start an ooniprobe
    test!
    """

    global_options = setupGlobalOptions(logging, start_tor, check_incoherences)

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
        global_options['annotations'] = setupAnnotations(global_options)

    if global_options['no-collector']:
        log.msg("Not reporting using a collector")
        global_options['collector'] = None
        start_tor = False
    else:
        start_tor = True

    if global_options['collector']:
        start_tor |= True

    return runTestWithDirector(director=director,
                               start_tor=start_tor,
                               global_options=global_options,
                               check_incoherences=check_incoherences)


# this variant version of runWithDirector splits the process in two,
# allowing a single director instance to be reused with multiple decks.

def runWithDaemonDirector(logging=True, start_tor=True, check_incoherences=True):
    """
    Instance the director, parse command line options and start an ooniprobe
    test!
    """

    try:
        import pika
        from pika import exceptions
        from pika.adapters import twisted_connection
    except ImportError:
        print "Pika is required for queue connection."
        print "Install with \"pip install pika\"."
        sys.exit(7)


    global_options = setupGlobalOptions(logging, start_tor, check_incoherences)

    director = Director()

    if global_options.get('annotations') is not None:
        global_options['annotations'] = setupAnnotations(global_options)

    if global_options['no-collector']:
        log.msg("Not reporting using a collector")
        global_options['collector'] = None
        start_tor = False
    else:
        start_tor = True

    finished = defer.Deferred()

    @defer.inlineCallbacks
    def readmsg(_, channel, queue_object, consumer_tag, counter):

        # Wait for a message and decode it.
        if counter >= lifetime:
            log.msg("Counter")
            queue_object.close(LifetimeExceeded())
            yield channel.basic_cancel(consumer_tag=consumer_tag)
            finished.callback(None)

        else:
            log.msg("Waiting for message")

            try:
                ch, method, properties, body = yield queue_object.get()
                log.msg("Got message")
                data = json.loads(body)
                counter += 1

                log.msg("Received %d/%d: %s" % (counter, lifetime, data['url'],))
                # acknowledge the message
                ch.basic_ack(delivery_tag=method.delivery_tag)

                d = runTestWithDirector(director=director,
                                        start_tor=start_tor,
                                        global_options=global_options,
                                        url=data['url'].encode('utf8'),
                                        check_incoherences=check_incoherences)
                # When the test has been completed, go back to waiting for a message.
                d.addCallback(readmsg, channel, queue_object, consumer_tag, counter+1)
            except exceptions.AMQPError,v:
                log.msg("Error")
                log.exception(v)
                finished.errback(v)



    @defer.inlineCallbacks
    def runQueue(connection, name, qos):
        # Set up the queue consumer.  When a message is received, run readmsg
        channel = yield connection.channel()
        yield channel.basic_qos(prefetch_count=qos)
        queue_object, consumer_tag = yield channel.basic_consume(
                                                   queue=name,
                                                   no_ack=False)
        readmsg(None, channel, queue_object, consumer_tag, 0)



    # Create the AMQP connection.  This could be refactored to allow test URLs
    # to be submitted through an HTTP server interface or something.
    urlp = urlparse.urlparse(config.global_options['queue'])
    urlargs = dict(urlparse.parse_qsl(urlp.query))

    # random lifetime requests counter
    lifetime = random.randint(820, 1032)

    # AMQP connection details are sent through the cmdline parameter '-Q'
    creds = pika.PlainCredentials(urlp.username or 'guest',
                                  urlp.password or 'guest')
    parameters = pika.ConnectionParameters(urlp.hostname,
                                           urlp.port or 5672,
                                           urlp.path.rsplit('/',1)[0] or '/',
                                           creds,
                                           heartbeat_interval=120,
                                           )
    cc = protocol.ClientCreator(reactor,
                                twisted_connection.TwistedProtocolConnection,
                                parameters)
    d = cc.connectTCP(urlp.hostname, urlp.port or 5672)
    d.addCallback(lambda protocol: protocol.ready)
    # start the wait/process sequence.
    d.addCallback(runQueue, urlp.path.rsplit('/',1)[-1], int(urlargs.get('qos',1)))

    return finished
