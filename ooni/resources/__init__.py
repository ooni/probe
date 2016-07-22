import json

from twisted.python.filepath import FilePath

from ooni import __resources_version__ as resources_version
from ooni.settings import config

ooni_resources_url = ("https://github.com/TheTorProject/ooni-probe/releases"
                      "/download/v{}/"
                      "ooni-resources.tar.gz").format(resources_version)

def get_download_url(tag_name, filename):
    return ("https://github.com/OpenObservatory/ooni-resources/releases"
            "/download/{0}/{1}".format(tag_name, filename))

def get_current_version():
    manifest = FilePath(config.resources_directory).child("manifest.json")
    if not manifest.exists():
        return 0
    with manifest.open("r") as f:
        manifest = json.load(f)
    return int(manifest["version"])
