from __future__ import print_function

import json

from .bases import ConfigTestCase
from ooni.ui.web.server import WebUIAPI

from mock import patch, Mock

class TestWebUIServer(ConfigTestCase):
    def setUp(self):
        super(TestWebUIServer, self).setUp()

        director = Mock()
        scheduler = Mock()

        self.wui_api = WebUIAPI(self.config, director, scheduler)

    def tearDown(self):
        super(TestWebUIServer, self).tearDown()
        self.wui_api.status_poller.stop()
        self.wui_api.director_event_poller.stop()

    def test_api_status(self):
        request = Mock()
        resp = self.wui_api.api_status(request)
        j = json.loads(resp)
        expected_keys = ["software_version", "software_name", "asn",
                         "country_code", "director_started", "initialized",
                         "quota_warning"]
        for key in expected_keys:
            self.assertTrue(key in j)
