from ooni.resources import get_out_of_date_resources, check_for_update
from ooni.tests.bases import ConfigTestCase

SAMPLE_CURRENT_MANIFEST = {
    "resources": [
        {
            "version": 0,
            "path": "some/file-to-update.txt"
        },
        {
            "version": 0,
            "path": "some/file-stays-stame.txt"
        },
        {
            "version": 0,
            "path": "some/file-to-delete.txt"
        }
    ]
}

SAMPLE_NEW_MANIFEST = {
    "resources": [
        {
            "version": 1,
            "path": "some/file-to-update.txt"
        },
        {
            "version": 0,
            "path": "some/file-stays-stame.txt"
        }
    ]
}
class TestResourceUpdate(ConfigTestCase):
    def test_check_for_updates(self):
        self.skipTest("Too long without mocks...")
        return check_for_update()

    def test_resources_out_of_date(self):
        paths_to_update, paths_to_delete = get_out_of_date_resources(
            SAMPLE_CURRENT_MANIFEST, SAMPLE_NEW_MANIFEST)
        self.assertEqual(paths_to_update[0]["path"], "some/file-to-update.txt")
        self.assertEqual(paths_to_delete[0]["path"], "some/file-to-delete.txt")
