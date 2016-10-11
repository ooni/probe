import sys

import os
import json
import random
import textwrap
import urlparse

from twisted.python import usage
from twisted.internet import defer

from ooni import errors, __version__
from ooni.settings import config, OONIPROBE_ROOT
from ooni.utils import log

class LifetimeExceeded(Exception): pass

class Options(usage.Options):
    synopsis = """%s [options] [path to test].py
    """ % (os.path.basename(sys.argv[0]),)

    longdesc = ("ooniprobe loads and executes a suite or a set of suites of"
                " network tests. These are loaded from modules, packages and"
                " files listed on the command line.")

    optFlags = [["help", "h"],
                ["no-collector", "n", "Disable writing to collector"],
                ["no-njson", "N", "Disable writing to disk"],
                ["no-geoip", "g", "Disable geoip lookup on start"],
                ["list", "s", "List the currently installed ooniprobe "
                              "nettests"],
                ["verbose", "v", "Show more verbose information"],
                ["web-ui", "w", "Start the web UI"],
                ["initialize", "z", "Initialize ooniprobe to begin running "
                                    "it"],
                ]

    optParameters = [
        ["reportfile", "o", None, "Specify the report file name to write "
                                  "to."],
        ["testdeck", "i", None, "Specify as input a test deck: a yaml file "
                                 "containing the tests to run and their "
                                "arguments."],
        ["collector", "c", None, "Specify the address of the collector for "
                                 "test results. In most cases a user will "
                                 "prefer to specify a bouncer over this."],
        ["bouncer", "b", None, "Specify the bouncer used to "
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
        ["preferred-backend", "P", None, "Set the preferred backend to use "
                                         "when submitting results and/or "
                                         "communicating with test helpers. "
                                         "Can be either onion, "
                                         "https or cloudfront"],
        ["queue", "Q", None, "AMQP Queue URL amqp://user:pass@host:port/vhost/queue"]
    ]

    compData = usage.Completions(
        extraActions=[usage.CompleteFiles(
            "*.py", descr="file | module | package | TestCase | testMethod",
            repeat=True)],)

    tracer = None

    def __init__(self):
        usage.Options.__init__(self)

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
        if self['testdeck'] or self['list'] or self['web-ui']:
            return
        try:
            self['test_file'] = args[0]
            self['subargs'] = args[1:]
        except:
            raise usage.UsageError("No test filename specified!")


def parseOptions():
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
                 errors.ConfigFileIncoherent,
                 SystemExit)

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


def initializeOoniprobe(global_options):
    print("It looks like this is the first time you are running ooniprobe")
    print("Please take a minute to read through the informed consent documentation and "
          "understand what are the risks associated with running ooniprobe.")
    print("Press enter to continue...")
    raw_input()
    with open(os.path.join(OONIPROBE_ROOT, 'ui', 'consent-form.md')) as f:
        consent_form_text = ''.join(f.readlines())
    from pydoc import pager
    pager(consent_form_text)

    answer = ""
    while answer.lower() != "yes":
        print('Type "yes" if you are fully aware of the risks associated with using ooniprobe and you wish to proceed')
        answer = raw_input("> ")

    print("")
    print("Now help us configure some things!")
    answer = raw_input('Should we upload measurements to a collector? (Y/n) ')
    should_upload = True
    if answer.lower().startswith("n"):
        should_upload = False

    answer = raw_input('Should we include your IP in measurements? (y/N) ')
    include_ip = False
    if answer.lower().startswith("y"):
        include_ip = True

    answer = raw_input('Should we include your ASN (your network) in '
                       'measurements? (Y/n) ')
    include_asn = True
    if answer.lower().startswith("n"):
        include_asn = False

    answer = raw_input('Should we include your Country in '
                       'measurements? (Y/n) ')
    include_country = True
    if answer.lower().startswith("n"):
        include_country = False

    answer = raw_input('How would you like reports to be uploaded? (onion, '
                       'https, cloudfront) ')

    preferred_backend = 'onion'
    if answer.lower().startswith("https"):
        preferred_backend = 'https'
    elif answer.lower().startswith("cloudfront"):
        preferred_backend = 'cloudfront'

    config.create_config_file(include_ip=include_ip,
                              include_asn=include_asn,
                              include_country=include_country,
                              should_upload=should_upload,
                              preferred_backend=preferred_backend)
    config.set_initialized()

def setupGlobalOptions(logging, start_tor, check_incoherences):
    global_options = parseOptions()

    config.global_options = global_options

    if not config.is_initialized():
        log.err("You first need to agree to the informed consent and setup "
                "ooniprobe to run it.")
        global_options['initialize'] = True
        return global_options

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

    if config.privacy.includepcap or global_options['pcapfile']:
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
    from ooni.backend_client import CollectorClient

    if global_options['collector']:
        collector_client = CollectorClient(global_options['collector'])
    elif config.reports.get('collector', None) is not None:
        collector_client = CollectorClient(config.reports['collector'])
    if not collector_client.isSupported():
        raise errors.CollectorUnsupported
    return collector_client

def createDeck(global_options, url=None):
    from ooni.deck import NGDeck
    from ooni.deck.legacy import subargs_to_options

    if url:
        log.msg("Creating deck for: %s" % (url))

    test_deck_path = global_options.pop('testdeck', None)
    test_name = global_options.pop('test_file', None)
    no_collector = global_options.pop('no-collector', False)
    try:
        if test_deck_path is not None:
            deck = NGDeck(
                global_options=global_options,
                no_collector=no_collector
            )
            deck.open(test_deck_path)
        else:
            deck = NGDeck(
                global_options=global_options,
                no_collector=no_collector,
                arbitrary_paths=True
            )
            log.debug("No test deck detected")
            if url is not None:
                args = ('-u', url)
            else:
                args = tuple()
            if any(global_options['subargs']):
                args = global_options['subargs'] + args

            test_options = subargs_to_options(args)
            test_options['test_name'] = test_name
            deck.load({
                "tasks": [
                    {"ooni": test_options}
                ]
            })
    except errors.MissingRequiredOption as option_name:
        log.err('Missing required option: "%s"' % option_name)
        incomplete_net_test_loader = option_name.net_test_loader
        map(log.msg, incomplete_net_test_loader.usageOptions().getUsage().split("\n"))
        raise SystemExit(2)

    except errors.NetTestNotFound as path:
        log.err('Requested NetTest file not found (%s)' % path)
        raise SystemExit(3)

    except errors.OONIUsageError as e:
        log.exception(e)
        map(log.msg, e.net_test_loader.usageOptions().getUsage().split("\n"))
        raise SystemExit(4)

    except errors.HTTPSCollectorUnsupported:
        log.err("HTTPS collectors require a twisted version of at least 14.0.2.")
        raise SystemExit(6)
    except errors.InsecureBackend:
        log.err("Attempting to report to an insecure collector.")
        log.err("To enable reporting to insecure collector set the "
                "advanced->insecure_backend option to true in "
                "your ooniprobe.conf file.")
        raise SystemExit(7)
    except Exception as e:
        if config.advanced.debug:
            log.exception(e)
        log.err(e)
        raise SystemExit(5)

    return deck


def runTestWithDirector(director, global_options, url=None,
                        start_tor=True,
                        create_input_store=True):
    deck = createDeck(global_options, url=url)

    d = director.start(create_input_store=create_input_store)
    @defer.inlineCallbacks
    def post_director_start(_):
        try:
            yield deck.setup()
            yield deck.run(director)
        except errors.UnableToLoadDeckInput as error:
            raise defer.failure.Failure(error)
        except errors.NoReachableTestHelpers as error:
            raise defer.failure.Failure(error)
        except errors.NoReachableCollectors as error:
            raise defer.failure.Failure(error)
        except SystemExit as error:
            raise error

    d.addCallback(post_director_start)
    d.addErrback(director_startup_handled_failures)
    d.addErrback(director_startup_other_failures)
    return d

def runWithDirector(global_options, create_input_store=True):
    """
    Instance the director, parse command line options and start an ooniprobe
    test!
    """
    from ooni.director import Director
    start_tor = False
    director = Director()
    if global_options['list']:
        net_tests = [net_test for net_test in director.getNetTests().items()]
        log.msg("")
        log.msg("Installed nettests")
        log.msg("==================")
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
            map(log.msg, desc.split("\n"))
            log.msg("Note: Third party tests require an external "
                    "application to run properly.")

        raise SystemExit(0)

    if global_options.get('annotations') is not None:
        global_options['annotations'] = setupAnnotations(global_options)

    if global_options.get('preferred-backend') is not None:
        config.advanced.preferred_backend = global_options['preferred-backend']

    if global_options['no-collector']:
        log.msg("Not reporting using a collector")
        global_options['collector'] = None
        start_tor = False
    elif config.advanced.get("preferred_backend", "onion") == "onion":
        start_tor = True

    if (global_options['collector'] and
            config.advanced.get("preferred_backend", "onion") == "onion"):
        start_tor |= True

    return runTestWithDirector(
        director=director,
        start_tor=start_tor,
        global_options=global_options,
        create_input_store=create_input_store
    )


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
        raise SystemExit(7)

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
            except exceptions.AMQPError, v:
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
