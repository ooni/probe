from __future__ import print_function

import os
import sys

from twisted.internet import defer, task
from twisted.python import usage

from ooni.utils import mkdir_p
from ooni.otime import prettyDateNowUTC
from ooni import errors
from ooni.geoip import probe_ip
from ooni.resources import check_for_update
from ooni.deck import NGDeck
from ooni import __version__

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
         "Specify the path where we should be writing the deck to."]
    ]

    def opt_version(self):
        print("oonideckgen version: " % __version__)
        sys.exit(0)

def generate_deck(options):

    deck_data = {
        "name": "Default ooniprobe deck",
        "description": "Default ooniprobe deck generated on {0}".format(
                       prettyDateNowUTC()),
        "schedule": "@daily",
        "tasks": [
            {
                "ooni": {
                    "test_name": "http_invalid_request_line"
                },
            },
            {
                "ooni": {
                    "test_name": "http_header_field_manipulation"
                },
            },
            {
                "ooni": {
                    "test_name": "web_connectivity",
                    "file": "$citizenlab_${probe_cc}_urls"
                },
            },
            {
                "ooni": {
                    "test_name": "web_connectivity",
                    "file": "$citizenlab_global_urls"
                }
            }
        ]
    }
    if options["collector"] is not None:
        deck_data["collector"] = options['collector']

    if options["bouncer"] is not None:
        deck_data["bouncer"] = options['bouncer']

    deck = NGDeck(deck_data=deck_data)
    with open(options['output'], 'w+') as fw:
        deck.write(fw)

    print("Deck written to {0}".format(options['output']))
    print("Run ooniprobe like so:")
    print("ooniprobe -i {0}".format(options['output']))


@defer.inlineCallbacks
def get_user_country_code():
    yield probe_ip.lookup(include_country=True)
    defer.returnValue(probe_ip.geodata['countrycode'])


@defer.inlineCallbacks
def oonideckgen(reactor):
    options = Options()
    try:
        options.parseOptions()
    except usage.UsageError as error_message:
        print("%s: %s" % (sys.argv[0], error_message))
        print(options)
        sys.exit(1)

    print("Checking for update of resources")
    yield check_for_update()

    if not options['output']:
        options['output'] = os.getcwd()

    if not options['country-code']:
        try:
            options['country-code'] = yield get_user_country_code()
        except errors.ProbeIPUnknown:
            print("Could not determine your IP address.")
            print("Check your internet connection or specify a country code "
                  "with -c.")
            sys.exit(4)

    if len(options['country-code']) != 2:
        print("%s: --country-code must be 2 characters" % sys.argv[0])
        sys.exit(2)

    if os.path.isdir(options['output']):
        options['output'] = os.path.join(options['output'], 'web-full.yaml')

    options['country-code'] = options['country-code'].lower()

    mkdir_p(os.path.dirname(options['output']))

    generate_deck(options)

def run():
    task.react(oonideckgen)

if __name__ == "__main__":
    run()
