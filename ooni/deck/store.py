import csv
import json
from copy import deepcopy

from twisted.internet import defer
from twisted.python.filepath import FilePath

from ooni.deck.deck import NGDeck
from ooni.otime import timestampNowISO8601UTC
from ooni.resources import check_for_update
from ooni.settings import config
from ooni.utils import log

class InputNotFound(Exception):
    pass

class DeckNotFound(Exception):
    pass

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
            in_file = self.resources.child("citizenlab-test-lists").child("{0}.csv".format(cc))
            if not in_file.exists():
                yield check_for_update(country_code)

            if not in_file.exists():
                continue

            # XXX maybe move this to some utility function.
            # It's duplicated in oonideckgen.
            data_fname = "citizenlab-test-lists_{0}.txt".format(cc)
            desc_fname = "citizenlab-test-lists_{0}.desc".format(cc)

            out_file = self.path.child("data").child(data_fname)
            out_fh = out_file.open('w')
            with in_file.open('r') as in_fh:
                csvreader = csv.reader(in_fh)
                csvreader.next()
                for row in csvreader:
                    out_fh.write("%s\n" % row[0])
            out_fh.close()

            desc_file = self.path.child("descriptors").child(desc_fname)
            with desc_file.open('w') as out_fh:
                if cc == "global":
                    name = "List of globally accessed websites"
                else:
                    # XXX resolve this to a human readable country name
                    country_name = cc
                    name = "List of websites for {0}".format(country_name)
                json.dump({
                    "name": name,
                    "filepath": out_file.path,
                    "last_updated": timestampNowISO8601UTC(),
                    "id": "citizenlab_{0}_urls".format(cc),
                    "type": "file/url"
                }, out_fh)
        self._cache_stale = True

    @defer.inlineCallbacks
    def create(self, country_code=None):
        # XXX This is a hax to avoid race conditions in testing because this
        #  object is a singleton and config can have a custom home directory
        #  passed at runtime.
        self.path = FilePath(config.inputs_directory)
        self.resources = FilePath(config.resources_directory)

        self.path.child("descriptors").makedirs(ignoreExistingDirectory=True)
        self.path.child("data").makedirs(ignoreExistingDirectory=True)
        yield self.update_url_lists(country_code)

    @defer.inlineCallbacks
    def update(self, country_code=None):
        # XXX why do we make a difference between create and update?
        yield self.create(country_code)

    def _update_cache(self):
        descs = self.path.child("descriptors")
        if not descs.exists():
            self._cache = {}
            return

        for fn in descs.listdir():
            with descs.child(fn).open("r") as in_fh:
                input_desc = json.load(in_fh)
                self._cache[input_desc.pop("id")] = input_desc
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
            input_desc = self._cache[input_id]
        except KeyError:
            raise InputNotFound(input_id)
        return input_desc

    def getContent(self, input_id):
        input_desc = self.get(input_id)
        with open(input_desc["filepath"]) as fh:
            return fh.read()


class DeckStore(object):
    def __init__(self):
        self.path = FilePath(config.decks_directory)
        self._cache = {}
        self._cache_stale = True

    def list(self):
        decks = []
        if self._cache_stale:
            self._update_cache()
        for deck_id, deck in self._cache.iteritems():
            decks.append((deck_id, deck))
        return decks

    def _update_cache(self):
        for deck_path in self.path.listdir():
            if not deck_path.endswith('.yaml'):
                continue
            deck_id = deck_path[:-1*len('.yaml')]
            deck = NGDeck(
                deck_path=self.path.child(deck_path).path
            )
            self._cache[deck_id] = deck

    def get(self, deck_id):
        if self._cache_stale:
            self._update_cache()
        try:
            return self._cache[deck_id]
        except KeyError:
            raise DeckNotFound(deck_id)

deck_store = DeckStore()
input_store = InputStore()
