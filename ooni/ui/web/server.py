import os
import re

from twisted.web import resource, static

from .resources import DecksGenerate, DecksStart
from .resources import DecksStop, DecksStatus
from .resources import DecksList

from .resources import TestsStart, TestsStop
from .resources import TestsStatus, TestsList

from .resources import Results

def rpath(*path):
    current_dir = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(current_dir, *path)

class TopLevel(resource.Resource):
    routes = [
        ('^/decks/generate$', DecksGenerate),
        ('^/decks/(.*)/start$', DecksStart),
        ('^/decks/(.*)/stop$', DecksStop),
        ('^/decks/(.*)$', DecksStatus),
        ('^/decks$', DecksList),
        ('^/net-tests/(.*)/start$', TestsStart),
        ('^/net-tests/(.*)/stop$', TestsStop),
        ('^/net-tests/(.*)$', TestsStatus),
        ('^/net-tests$', TestsList),
        ('^/results$', Results)
    ]

    def __init__(self, config, director):
        resource.Resource.__init__(self)

        self._director = director
        self._config = config
        self._route_map = map(lambda x: (re.compile(x[0]), x[1]), self.routes)

        self.putChild("static", static.File(rpath("static")))

    def getChild(self, path, request):
        if path == "":
            return self

        for route, r in self._route_map:
            match = route.search(request.path)
            if match:
                return r(self._director, *match.groups())

        return resource.NoResource("Invalid path requested")

    def render_GET(self, request):
        with open(rpath("static", "index.html")) as f:
            return f.read()
