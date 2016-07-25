import json

from twisted.python.filepath import FilePath
from twisted.internet import defer
from twisted.web.client import downloadPage, getPage

from ooni.utils import log
from ooni.settings import config

class UpdateFailure(Exception):
    pass

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

@defer.inlineCallbacks
def get_latest_version():
    """
    Fetches the latest version of the resources package.
    :return: (int) the latest version number
    """
    try:
        version = yield getPage(get_download_url("latest", "version"))
    except Exception as exc:
        raise exc
    defer.returnValue(int(version.strip()))


def get_out_of_date_resources(current_manifest, new_manifest,
                              country_code=None):
    current_res = {}
    new_res = {}
    for r in current_manifest["resources"]:
        current_res[r["path"]] = r

    for r in new_manifest["resources"]:
        new_res[r["path"]] = r

    paths_to_delete = [
        current_res[path] for path in list(set(current_res.keys()) -
                                           set(new_res.keys()))
        ]
    paths_to_update = []
    _resources = FilePath(config.resources_directory)
    for path, info in new_res.items():
        if (country_code is not None and
                info["country_code"] != "ALL" and
                info["country_code"] != country_code):
            continue
        if current_res.get(path, None) is None:
            paths_to_update.append(info)
        elif current_res[path]["version"] < info["version"]:
            paths_to_update.append(info)
        else:
            pre_path, filename = info["path"].split("/")
            # Also perform an update when it doesn't exist on disk, although
            #  the manifest claims we have a more up to date version.
            # This happens if an update by country_code happened and a new
            # country code is now required.
            if not _resources.child(pre_path).child(filename).exists():
                paths_to_update.append(info)

    return paths_to_update, paths_to_delete

@defer.inlineCallbacks
def check_for_update(country_code=None):
    """
    Checks if we need to update the resources.
    If the country_code is specified then only the resources for that
    country will be updated/downloaded.
    :return: the latest version.
    """
    temporary_files = []
    def cleanup():
        # If we fail we need to delete all the temporary files
        for _, src_file_path in temporary_files:
            src_file_path.remove()

    current_version = get_current_version()
    latest_version = yield get_latest_version()

    # We are already at the latest version
    if current_version == latest_version:
        defer.returnValue(latest_version)

    resources_dir = FilePath(config.resources_directory)
    resources_dir.makedirs(ignoreExistingDirectory=True)
    current_manifest = resources_dir.child("manifest.json")

    new_manifest = current_manifest.temporarySibling()
    new_manifest.alwaysCreate = 0

    temporary_files.append((current_manifest, new_manifest))

    try:
        yield downloadPage(
            get_download_url(latest_version, "manifest.json"),
            new_manifest.path
        )
    except:
        cleanup()
        raise UpdateFailure("Failed to download manifest")

    new_manifest_data = json.loads(new_manifest.getContent())

    if current_manifest.exists():
        with current_manifest.open("r") as f:
            current_manifest_data = json.loads(f)
    else:
        current_manifest_data = {
            "resources": []
        }

    to_update, to_delete = get_out_of_date_resources(
            current_manifest_data, new_manifest_data, country_code)

    try:
        for resource in to_update:
            pre_path, filename = resource["path"].split("/")
            dst_file = resources_dir.child(pre_path).child(filename)
            dst_file.parent().makedirs(ignoreExistingDirectory=True)
            src_file = dst_file.temporarySibling()
            src_file.alwaysCreate = 0

            temporary_files.append((dst_file, src_file))
            # The paths for the download require replacing "/" with "."
            download_url = get_download_url(latest_version,
                                            resource["path"].replace("/", "."))
            print("Downloading {0}".format(download_url))
            yield downloadPage(download_url, src_file.path)
    except Exception as exc:
        cleanup()
        log.exception(exc)
        raise UpdateFailure("Failed to download resource {0}".format(resource["path"]))

    for dst_file, src_file in temporary_files:
        log.msg("Moving {0} to {1}".format(src_file.path,
                                           dst_file.path))
        src_file.moveTo(dst_file)

    for resource in to_delete:
        log.msg("Deleting old resources")
        resources_dir.child(resource["path"]).remove()
