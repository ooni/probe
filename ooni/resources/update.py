import os
import tarfile
import tempfile

from twisted.python.filepath import FilePath
from twisted.internet import defer
from twisted.web.client import downloadPage

from ooni.settings import config
from ooni.resources import ooni_resources_url

@defer.inlineCallbacks
def download_resources():
    if os.access(config.var_lib_path, os.W_OK):
        dst_directory = FilePath(config.var_lib_path)
    else:
        dst_directory = FilePath(config.ooni_home)

    print("Downloading {} to {}".format(ooni_resources_url,
                                        dst_directory.path))
    tmp_download_directory = FilePath(tempfile.mkdtemp())
    tmp_download_filename = tmp_download_directory.temporarySibling()


    try:
        yield downloadPage(ooni_resources_url, tmp_download_filename.path)
        ooni_resources_tar_gz = tarfile.open(tmp_download_filename.path)
        ooni_resources_tar_gz.extractall(tmp_download_directory.path)

        if not tmp_download_directory.child('GeoIP').exists():
            raise Exception("Could not find GeoIP data files in downloaded "
                            "tar.")

        if not tmp_download_directory.child('resources').exists():
            raise Exception("Could not find resources data files in "
                            "downloaded tar.")

        geoip_dir = dst_directory.child('GeoIP')
        resources_dir = dst_directory.child('resources')

        if geoip_dir.exists():
            geoip_dir.remove()
        tmp_download_directory.child('GeoIP').moveTo(geoip_dir)

        if resources_dir.exists():
            resources_dir.remove()
        tmp_download_directory.child('resources').moveTo(resources_dir)

        print("Written GeoIP files to {}".format(geoip_dir.path))
        print("Written resources files to {}".format(resources_dir.path))

    except Exception as exc:
        print("Failed to download resources!")
        raise exc

    finally:
        tmp_download_directory.remove()
