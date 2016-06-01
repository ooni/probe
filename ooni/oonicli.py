import sys

import os
import json
import yaml
import random
import textwrap
import urlparse

from twisted.python import usage
from twisted.internet import defer

from ooni import errors, __version__, canonical_bouncer
from ooni.settings import config
from ooni.utils import log
from backend_client import CollectorClient

class LifetimeExceeded(Exception): pass

class Options(usage.Options):
    synopsis = """%s [options] [path to test].py
    """ % (os.path.basename(sys.argv[0]),)

    longdesc = ("ooniprobe loads and executes a suite or a set of suites of"
                " network tests. These are loaded from modules, packages and"
                " files listed on the command line.")

    optFlags = [["help", "h"],
                ["no-collector", "n", "Disable writing to collector"],
                ["no-yamloo", "N", "Disable writing to YAML file"],
                ["no-geoip", "g", "Disable geoip lookup on start"],
                ["list", "s", "List the currently installed ooniprobe "
                              "nettests"],
                ["printdeck", "p", "Print the equivalent deck for the "
                                   "provided command"],
                ["verbose", "v", "Show more verbose information"]
                ]

    optParameters = [
        ["reportfile", "o", None, "Specify the report file name to write to."],
        ["testdeck", "i", None, "Specify as input a test deck: a yaml file "
                                "containing the tests to run and their "
                                "arguments."],
        ["collector", "c", None, "Specify the address of the collector for "
                                 "test results. In most cases a user will "
                                 "prefer to specify a bouncer over this."],
        ["bouncer", "b", canonical_bouncer, "Specify the bouncer used to "
                                            "obtain the address of the "
                                            "collector and test helpers."],
        ["logfile", "l", None, "Write to this logs to this filename."],
        ["pcapfile", "O", None, "Write a PCAP of the ooniprobe session to "
                                "this filename."],
        ["configfile", "f", None, "Specify a path to the ooniprobe "
                                  "configuration file."],
        ["datadir", "d", None, "Specify a path to the ooniprobe data "
                               "directory."],
        ["annotations", "a", None, "Annotate the report with a key:value[, "
                                   "key:value] format."],
        ["queue", "Q", None, "AMQP Queue URL amqp://user:pass@host:port/vhost/queue"]
    ]

    compData = usage.Completions(
        extraActions=[usage.CompleteFiles(
            "*.py", descr="file | module | package | TestCase | testMethod",
            repeat=True)],)

    tracer = None

    def __init__(self):
        usage.Options.__init__(self)

    def getUsage(self, width=None):
        return super(Options, self).getUsage(width) + """
To get started you may want to run:

$ oonideckgen

This will tell you how to run ooniprobe :)
"""

    def opt_spew(self):
        """
        Print an insanely verbose log of everything that happens.
        Useful when debugging freezes or locks in complex code.
        """
        from twisted.python.util import spewer
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
        from ooni.utils.net import hasRawSocketPermission
        if hasRawSocketPermission():
            from ooni.utils.txscapy import ScapyFactory
            config.scapyFactory = ScapyFactory(config.advanced.interface)
        else:
            log.err("Insufficient Privileges to capture packets."
                    " See ooniprobe.conf privacy.includepcap")
            sys.exit(2)
    global_options['check_incoherences'] = check_incoherences
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

def setupCollector(global_options, collector_client):
    if global_options['collector']:
        collector_client = CollectorClient(global_options['collector'])
    elif config.reports.get('collector', None) is not None:
        collector_client = CollectorClient(config.reports['collector'])
    if not collector_client.isSupported():
        raise errors.CollectorUnsupported
    return collector_client

def createDeck(global_options, url=None):
    from ooni.nettest import NetTestLoader
    from ooni.deck import Deck, nettest_to_path

    if url:
        log.msg("Creating deck for: %s" % (url))

    if global_options['no-yamloo']:
        log.msg("Will not write to a yamloo report file")

    deck = Deck(bouncer=global_options['bouncer'],
                no_collector=global_options['no-collector'])

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
                                            test_file=test_file,
                                            annotations=global_options['annotations'])
            if global_options['collector']:
                net_test_loader.collector = \
                    CollectorClient(global_options['collector'])
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
    except errors.InsecureBackend:
        log.err("Attempting to report to an insecure collector.")
        log.err("To enable reporting to insecure collector set the "
                "advanced->insecure_backend option to true in "
                "your ooniprobe.conf file.")
        sys.exit(7)
    except Exception as e:
        if config.advanced.debug:
            log.exception(e)
        log.err(e)
        sys.exit(5)

    return deck


def runTestWithDirector(director, global_options, url=None, start_tor=True):
    deck = createDeck(global_options, url=url)

    start_tor |= deck.requiresTor

    d = director.start(start_tor=start_tor,
                       check_incoherences=global_options['check_incoherences'])

    def setup_nettest(_):
        try:
            return deck.setup()
        except errors.UnableToLoadDeckInput as error:
            return defer.failure.Failure(error)
        except errors.NoReachableTestHelpers as error:
            return defer.failure.Failure(error)
        except errors.NoReachableCollectors as error:
            return defer.failure.Failure(error)

    # Wait until director has started up (including bootstrapping Tor)
    # before adding tests
    @defer.inlineCallbacks
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
            collector_client = None
            if not global_options['no-collector']:
                collector_client = setupCollector(global_options,
                                                  net_test_loader.collector)

            yield director.startNetTest(net_test_loader,
                                        global_options['reportfile'],
                                        collector_client,
                                        global_options['no-yamloo'])

    d.addCallback(setup_nettest)
    d.addCallback(post_director_start)
    d.addErrback(director_startup_handled_failures)
    d.addErrback(director_startup_other_failures)
    return d

def runWithDirector(global_options):
    """
    Instance the director, parse command line options and start an ooniprobe
    test!
    """
    from ooni.director import Director
    director = Director()
    if global_options['list']:
        net_tests = [net_test for net_test in director.getNetTests().items()]
        print ""
        print "Installed nettests"
        print "=================="
        for net_test_id, net_test in net_tests:
            optList = []
            for name, details in net_test['arguments'].items():
                optList.append({'long': name, 'doc': details['description']})

            desc = ('\n' +
                    net_test['name'] +
                    '\n' +
                    '-'*len(net_test['name']) +
                    '\n' +
                    '\n'.join(textwrap.wrap(net_test['description'], 80)) +
                    '\n\n' +
                    '$ ooniprobe {}/{}'.format(net_test['category'],
                                                      net_test['id']) +
                    '\n\n' +
                    ''.join(usage.docMakeChunks(optList))
            )
            print desc
            print "Note: Third party tests require an external "\
                  "application to run properly."

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
                               global_options=global_options)


# this variant version of runWithDirector splits the process in two,
# allowing a single director instance to be reused with multiple decks.

def runWithDaemonDirector(global_options):
    """
    Instance the director, parse command line options and start an ooniprobe
    test!
    """
    from twisted.internet import reactor, protocol
    from ooni.director import Director
    try:
        import pika
        from pika import exceptions
        from pika.adapters import twisted_connection
    except ImportError:
        print "Pika is required for queue connection."
        print "Install with \"pip install pika\"."
        sys.exit(7)

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
                                        url=data['url'].encode('utf8'))
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
