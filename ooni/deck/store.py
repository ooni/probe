import csv
import json
import errno
from copy import deepcopy

from twisted.internet import defer
from twisted.python.filepath import FilePath

from ooni.utils import mkdir_p, log
from ooni.deck.deck import NGDeck
from ooni.otime import timestampNowISO8601UTC
from ooni.resources import check_for_update
from ooni.settings import config

# These are the decks to be run by default.
DEFAULT_DECKS = ['web', 'tor', 'im', 'http-invalid']

class InputNotFound(Exception):
    pass

class DeckNotFound(Exception):
    pass


def write_txt_from_csv(in_file, out_file, func, skip_header=True):
    with in_file.open('r') as in_fh, out_file.open('w') as out_fh:
        csvreader = csv.reader(in_fh)
        if skip_header:
            csvreader.next()
        for row in csvreader:
            out_fh.write(func(row))

def write_descriptor(out_file, name, desc_id, filepath, file_type):
    with out_file.open('w') as out_fh:
        json.dump({
            "name": name,
            "filepath": filepath,
            "last_updated": timestampNowISO8601UTC(),
            "id": desc_id,
            "type": file_type
        }, out_fh)

class InputStore(object):
    def __init__(self):
        self.path = FilePath(config.inputs_directory)
        self.resources = FilePath(config.resources_directory)
        self._cache_stale = True
        self._cache = {}

    @defer.inlineCallbacks
    def update_url_lists(self, country_code):
        countries = ["global"]
        if country_code != "ZZ":
            countries.append(country_code)

        for cc in countries:
            cc = cc.lower()
            in_file = self.resources.child("citizenlab-test-lists").child("{0}.csv".format(cc))
            if not in_file.exists():
                yield check_for_update(country_code)

            if not in_file.exists():
                log.msg("Could not find input for country "
                        "{0} in {1}".format(cc, in_file.path))
                continue

            # XXX maybe move this to some utility function.
            # It's duplicated in oonideckgen.
            data_fname = "citizenlab-test-lists_{0}.txt".format(cc)
            desc_fname = "citizenlab-test-lists_{0}.desc".format(cc)

            out_file = self.path.child("data").child(data_fname)
            write_txt_from_csv(in_file, out_file,
                lambda row: "{}\n".format(row[0])
            )

            desc_file = self.path.child("descriptors").child(desc_fname)
            if cc == "global":
                name = "List of globally accessed websites"
            else:
                # XXX resolve this to a human readable country name
                country_name = cc
                name = "List of websites for {0}".format(country_name)
            write_descriptor(desc_file, name,
                             "citizenlab_{0}_urls".format(cc),
                             out_file.path,
                             "file/url")

        self._cache_stale = True
        yield defer.succeed(None)

    @defer.inlineCallbacks
    def update_tor_bridge_lines(self, country_code):
        from ooni.utils import onion
        in_file = self.resources.child("tor-bridges").child(
            "tor-bridges-ip-port.csv"
        )
        if not in_file.exists():
            yield check_for_update(country_code)

        data_fname = "tor-bridge-lines.txt"
        desc_fname = "tor-bridge-lines.desc"
        out_file = self.path.child("data").child(data_fname)

        def format_row(row):
            host, port, nickname, protocol = row
            if protocol.lower() not in onion.pt_names:
                return "{}:{}\n".format(host, port)
            return "{} {}:{}\n".format(protocol, host, port)

        write_txt_from_csv(in_file, out_file, format_row)
        desc_file = self.path.child("descriptors").child(desc_fname)
        write_descriptor(
            desc_file, "Tor bridge lines",
            "tor_bridge_lines", out_file.path,
            "file/ip-port"
        )
        self._cache_stale = True

        # Do an empty defer to fit inside of a event loop clock
        yield defer.succeed(None)

    @defer.inlineCallbacks
    def create(self, country_code=None):
        # XXX This is a hax to avoid race conditions in testing because this
        #  object is a singleton and config can have a custom home directory
        #  passed at runtime.
        self.path = FilePath(config.inputs_directory)
        self.resources = FilePath(config.resources_directory)

        mkdir_p(self.path.child("descriptors").path)
        mkdir_p(self.path.child("data").path)

        yield self.update_url_lists(country_code)
        yield self.update_tor_bridge_lines(country_code)

    @defer.inlineCallbacks
    def update(self, country_code=None):
        # XXX why do we make a difference between create and update?
        yield self.create(country_code)

    def _update_cache(self):
        new_cache = {}
        descs = self.path.child("descriptors")
        if not descs.exists():
            self._cache = new_cache
            return

        for fn in descs.listdir():
            with descs.child(fn).open("r") as in_fh:
                input_desc = json.load(in_fh)
                new_cache[input_desc.pop("id")] = input_desc
        self._cache = new_cache
        self._cache_stale = False
        return

    def list(self):
        if self._cache_stale:
            self._update_cache()
        return deepcopy(self._cache)

    def get(self, input_id):
        if self._cache_stale:
            self._update_cache()
        try:
            input_desc = deepcopy(self._cache[input_id])
        except KeyError:
            raise InputNotFound(input_id)
        return input_desc

    def getContent(self, input_id):
        input_desc = self.get(input_id)
        with open(input_desc["filepath"]) as fh:
            return fh.read()


class DeckStore(object):
    def __init__(self, enabled_directory=config.decks_enabled_directory,
                 available_directory=config.decks_available_directory):
        self.enabled_directory = FilePath(enabled_directory)
        self.available_directory = FilePath(available_directory)
        self._cache = {}
        self._cache_stale = True

    def _list(self):
        if self._cache_stale:
            self._update_cache()
        for deck_id, deck in self._cache.iteritems():
            yield (deck_id, deck)

    def list(self):
        decks = []
        for deck_id, deck in self._list():
            decks.append((deck_id, deck))
        return decks

    def list_enabled(self):
        decks = []
        for deck_id, deck in self._list():
            if not self.is_enabled(deck_id):
                continue
            decks.append((deck_id, deck))
        return decks

    def is_enabled(self, deck_id):
        return self.enabled_directory.child(deck_id + '.yaml').exists()

    def enable(self, deck_id):
        deck_path = self.available_directory.child(deck_id + '.yaml')
        if not deck_path.exists():
            raise DeckNotFound(deck_id)
        deck_enabled_path = self.enabled_directory.child(deck_id + '.yaml')
        try:
            deck_path.linkTo(deck_enabled_path)
        except OSError as ose:
            if ose.errno != errno.EEXIST:
                raise

    def disable(self, deck_id):
        deck_enabled_path = self.enabled_directory.child(deck_id + '.yaml')
        if not deck_enabled_path.exists():
            raise DeckNotFound(deck_id)
        deck_enabled_path.remove()

    def _update_cache(self):
        new_cache = {}
        for deck_path in self.available_directory.listdir():
            if not deck_path.endswith('.yaml'):
                continue
            deck = NGDeck(
                deck_path=self.available_directory.child(deck_path).path
            )
            new_cache[deck.id] = deck
        self._cache = new_cache
        self._cache_stale = False

    def get(self, deck_id):
        if self._cache_stale:
            self._update_cache()
        try:
            return deepcopy(self._cache[deck_id])
        except KeyError:
            raise DeckNotFound(deck_id)

deck_store = DeckStore()
input_store = InputStore()
