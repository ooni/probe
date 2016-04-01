import os
import re
from twisted.web import resource, static

from .resources import DecksGenerate, DecksStart, DecksStop
from .resources import DecksStatus, DecksList, TestsStart
from .resources import TestsStop, TestsStatus, TestsList
from .resources import Results


class OONIProbeWebRoot(resource.Resource):
    routes = [
        ('^/decks/generate$', DecksGenerate),
        ('^/decks/(.*)/start$', DecksStart),
        ('^/decks/(.*)/stop$', DecksStop),
        ('^/decks/(.*)$', DecksStatus),
        ('^/decks$', DecksList),
        ('^/tests/(.*)/start$', TestsStart),
        ('^/tests/(.*)/stop$', TestsStop),
        ('^/tests/(.*)$', TestsStatus),
        ('^/tests$', TestsList),
        ('^/results$', Results)
    ]

    def __init__(self, config, director):
        resource.Resource.__init__(self)

        self._director = director
        self._config = config
        self._route_map = map(lambda x: (re.compile(x[0]), x[1]), self.routes)

        wui_directory = os.path.join(self._config.data_directory, 'ui', 'app')
        self._static = static.File(wui_directory)

    def getChild(self, path, request):
        for route, r in self._route_map:
            match = route.search(request.path)
            if match:
                return r(self._director, *match.groups())
        return self._static.getChild(path, request)
