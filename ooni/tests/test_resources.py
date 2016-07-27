import os
import shutil
import tempfile

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
        tmp_dir = tempfile.mkdtemp()
        os.mkdir(os.path.join(tmp_dir, 'some'))
        original_paths = map(lambda r: r['path'],
                             SAMPLE_CURRENT_MANIFEST['resources'])
        for path in original_paths:
            with open(os.path.join(tmp_dir, path), 'w+'):
                pass
        paths_to_update, paths_to_delete = get_out_of_date_resources(
            SAMPLE_CURRENT_MANIFEST, SAMPLE_NEW_MANIFEST,
            resources_directory=tmp_dir)
        self.assertEqual(paths_to_update[0]["path"], "some/file-to-update.txt")
        self.assertEqual(paths_to_delete[0]["path"], "some/file-to-delete.txt")

        shutil.rmtree(tmp_dir)
