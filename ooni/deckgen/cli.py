import os
import sys
import copy
import errno

import yaml

from twisted.python import usage

from . import __version__
from ooni.resources import inputs
from ooni.settings import config


class Options(usage.Options):
    synopsis = """%s [options]
    """

    optParameters = [
        ["country-code", "c",
         None,
         "Specify the two letter country code for which we should "
         "generate the deck."
         ],
        ["output", "o",
         None,
         "Specify the directory where to write output."
         ]
    ]

    def opt_version(self):
        print("oonideckgen version: %s" % __version__)
        sys.exit(0)

    def postOptions(self):
        if not self['output'] or not self['country-code']:
            raise usage.UsageError(
                "Both --output and --country-code are required"
            )
        if len(self['country-code']) != 2:
            raise usage.UsageError("--country-code must be 2 characters")
        if not os.path.isdir(self['output']):
            raise usage.UsageError("%s is not a directory" % self['output'])

        self['country-code'] = self['country-code'].lower()

        output_dir = os.path.abspath(self['output'])
        output_dir = os.path.join(output_dir,
                                  "deck-%s" % self['country-code'])
        self['output'] = output_dir


class Deck():
    _base_entry = {
        "options": {
            "collector": None,
            "help": 0,
            "logfile": None,
            "no-default-reporter": 0,
            "parallelism": None,
            "pcapfile": None,
            "reportfile": None,
            "resume": 0,
            "testdeck": None
        }
    }

    def __init__(self):
        self.deck = []

    def add_test(self, test_file, subargs=[]):
        deck_entry = copy.deepcopy(self._base_entry)
        deck_entry['options']['test_file'] = test_file
        deck_entry['options']['subargs'] = subargs
        self.deck.append(deck_entry)

    def pprint(self):
        print yaml.safe_dump(self.deck)

    def write_to_file(self, filename):
        with open(filename, "w+") as f:
            f.write(yaml.safe_dump(self.deck))


def usage():
    print "%s <two letter country code> <output dir>" % sys.argv[0]


def run():
    options = Options()
    try:
        options.parseOptions()
    except usage.UsageError as error_message:
        print "%s: %s" % (sys.argv[0], error_message)
        print "%s: Try --help for usage details." % (sys.argv[0])
        sys.exit(1)

    config.read_config_file()

    try:
        os.makedirs(options['output'])
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise
    dns_servers_processor = inputs['namebench-dns-servers.csv']['processor']
    url_lists_processor = inputs['citizenlab-test-lists.zip']['processor']

    try:
        url_list_country = url_lists_processor.generate_country_input(
            options['country-code'],
            options['output']
        )

    except Exception:
        print "Could not generate country specific url list"
        print "We will just use the global one."
        url_list_country = None

    url_list_global = url_lists_processor.generate_global_input(
        options['output']
    )
    dns_servers = dns_servers_processor.generate_country_input(
        options['country-code'],
        options['output']
    )

    deck = Deck()
    # deck.add_test('manipulation/http_host', ['-f', 'somefile.txt'])
    deck.add_test('blocking/http_requests', ['-f', url_list_global])
    deck.add_test('blocking/dns_consistency',
                  ['-f', url_list_global, '-T', dns_servers])

    if url_list_country is not None:
        deck.add_test('blocking/dns_consistency',
                      ['-f', url_list_country, '-T', dns_servers])
        deck.add_test('blocking/http_requests', ['-f', url_list_country])

    deck.add_test('manipulation/http_invalid_request_line')
    deck.add_test('manipulation/http_header_field_manipulation')
    # deck.add_test('manipulation/traceroute')
    deck.pprint()
    deck_filename = os.path.join(options['output'],
                                 "%s-%s-user.deck" % (__version__,
                                                      options['country-code']))
    deck.write_to_file(deck_filename)
    print "Deck written to %s" % deck_filename
    print "Run ooniprobe like so:"
    print "ooniprobe -i %s" % deck_filename

if __name__ == "__main__":
    run()
