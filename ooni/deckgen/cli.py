import os
import sys
import copy
import errno

import yaml

from twisted.internet import defer
from twisted.python import usage

from ooni import errors
from ooni.geoip import ProbeIP
from ooni.settings import config

from ooni.deckgen import __version__
from ooni.deckgen.processors import citizenlab_test_lists
from ooni.deckgen.processors import namebench_dns_servers
from ooni.resources.update import download_resources

class Options(usage.Options):
    synopsis = """%s [options]
    """ % sys.argv[0]

    optParameters = [
        ["country-code", "c", None,
         "Specify the two letter country code for which we should "
         "generate the deck."],
        ["collector", None, None, "Specify a custom collector to use when "
                                  "submitting reports"],
        ["bouncer", None, None, "Specify a custom bouncer to use"],
        ["output", "o", None,
         "Specify the directory where to write output."]
    ]

    def opt_version(self):
        print("oonideckgen version: %s" % __version__)
        sys.exit(0)


class Deck(object):
    _base_entry = {
        "options": {
            "test_file": None,
            "subargs": [],
            "annotations": None,

            "collector": None,
            "bouncer": None,

            "reportfile": None,

            "no-collector": 0,
            "no-geoip": 0,
            "no-yamloo": 0,
            "verbose": 0
        }
    }

    def __init__(self, collector=None, bouncer=None):
        self.deck_entries = []
        self.collector = collector
        self.bouncer = bouncer

    def add_test(self, test_file, subargs=[]):
        deck_entry = copy.deepcopy(self._base_entry)
        deck_entry['options']['collector'] = self.collector
        deck_entry['options']['bouncer'] = self.bouncer
        deck_entry['options']['test_file'] = test_file
        deck_entry['options']['subargs'] = subargs
        self.deck_entries.append(deck_entry)

    def pprint(self):
        print yaml.safe_dump(self.deck_entries)

    def write_to_file(self, filename):
        with open(filename, "w+") as f:
            f.write(yaml.safe_dump(self.deck_entries))


def generate_deck(options):
    url_list_country = None
    try:
        url_list_country = citizenlab_test_lists.generate_country_input(
            options['country-code'],
            options['output']
        )
    except Exception:
        print "Could not generate country specific url list"
        print "We will just use the global one."

    url_list_global = citizenlab_test_lists.generate_global_input(
        options['output']
    )

    deck = Deck(collector=options['collector'], bouncer=options['bouncer'])
    deck.add_test('manipulation/http_invalid_request_line')
    deck.add_test('manipulation/http_header_field_manipulation')

    if url_list_country is not None:
        deck.add_test('blocking/web_connectivity', ['-f', url_list_country])
    deck.add_test('blocking/web_connectivity', ['-f', url_list_global])

    if config.advanced.debug:
        deck.pprint()
    deck_filename = os.path.join(options['output'],
                                 "default-user.deck")
    deck.write_to_file(deck_filename)
    print "Deck written to %s" % deck_filename
    print "Run ooniprobe like so:"
    print "ooniprobe -i %s" % deck_filename


@defer.inlineCallbacks
def get_user_country_code():
    config.privacy.includecountry = True
    probe_ip = ProbeIP()
    yield probe_ip.lookup()
    defer.returnValue(probe_ip.geodata['countrycode'])

def resources_up_to_date():
    if config.get_data_file_path("GeoIP/GeoIP.dat") is None:
        return False

    if config.get_data_file_path("resources/"
                                 "namebench-dns-servers.csv") is None:
        return False

    if config.get_data_file_path("resources/"
                                 "citizenlab-test-lists/"
                                 "global.csv") is None:
        return False

    return True

@defer.inlineCallbacks
def run():
    options = Options()
    try:
        options.parseOptions()
    except usage.UsageError as error_message:
        print "%s: %s" % (sys.argv[0], error_message)
        print options
        sys.exit(1)

    if not resources_up_to_date():
        print("Resources for running ooniprobe are not up to date.")
        print("Will update them now.")
        yield download_resources()

    if not options['output']:
        options['output'] = os.getcwd()

    if not options['country-code']:
        try:
            options['country-code'] = yield get_user_country_code()
        except errors.ProbeIPUnknown:
            print "Could not determine your IP address."
            print "Check your internet connection or specify a country code with -c."
            sys.exit(4)

    if len(options['country-code']) != 2:
        print "%s: --country-code must be 2 characters" % sys.argv[0]
        sys.exit(2)

    if not os.path.isdir(options['output']):
        print "%s: %s is not a directory" % (sys.argv[0],
                                             options['output'])
        sys.exit(3)

    options['country-code'] = options['country-code'].lower()

    output_dir = os.path.abspath(options['output'])
    output_dir = os.path.join(output_dir,
                              "deck-%s" % options['country-code'])
    options['output'] = output_dir

    try:
        os.makedirs(options['output'])
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

    generate_deck(options)
