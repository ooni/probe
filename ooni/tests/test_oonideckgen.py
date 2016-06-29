import os
import yaml
import tempfile

from .bases import ConfigTestCase

from ooni.deckgen import cli

class TestOONIDeckgen(ConfigTestCase):
    def setUp(self):
        super(TestOONIDeckgen, self).setUp()
        test_lists_dir = os.path.join(self.config.ooni_home,
                                      "resources",
                                      "citizenlab-test-lists")
        try:
            os.makedirs(test_lists_dir)
        except Exception as exc:
            pass
        global_list = os.path.join(test_lists_dir, "global.csv")

        with open(global_list, 'w') as f:
            f.write("url,category_code,category_description,date_added,"
                    "source,notes\n")
            f.write("http://example.com,FOO,Foo,2016-04-15,OONI,\n")

    def test_generate_deck(self):
        temp_dir = tempfile.mkdtemp()
        cli.generate_deck({
            "country-code": "it",
            "output": temp_dir,
            "collector": None,
            "bouncer": None
        })
        with open(os.path.join(temp_dir, "default-user.deck")) as f:
            self.assertEqual(len(yaml.safe_load(f)), 3)
