#!/usr/bin/env python2
"""
This is the auto-updater script for lepidopter.

It must be run from root and it takes care of downloading the most recent
updates and doing all the operations needed to perform the update.

To run it expects systemd to be configured.

This script includes a self-installer which can be run via:

python updater.py install

It then expects to be run as a systemd service with:

python updater.py update --watch
"""

from __future__ import print_function

import os
import re
import imp # XPY3 this is deprecated in python3
import sys
import time
import errno
import shutil
import getpass
import logging
import tempfile
import argparse

from subprocess import check_output, check_call, CalledProcessError

# The version number of the updater
__version__ = "1.0.1"

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
# UPDATE_BASE_URL/latest/version must return an integer containing the latest version number
# UPDATE_BASE_URL/VERSION/update.py must return the update script for VERSION
# UPDATE_BASE_URL/VERSION/update.py.asc must return a valid GPG signature for update.py
UPDATE_BASE_URL = "https://github.com/OpenObservatory/lepidopter-update/releases/download/"

CURRENT_VERSION_PATH = "/etc/lepidopter-update/version"
UPDATER_PATH = "/opt/ooni/lepidopter-update/versions/"
SCRIPT_INSTALL_PATH = "/opt/ooni/lepidopter-update/updater.py"

SYSTEMD_SCRIPT_PATH = "/etc/systemd/system/lepidopter-update.service"
SYSTEMD_SCRIPT = """\
[Unit]
Description=lepidopter-update service

[Service]
Type=simple
ExecStart={0} --log-file /var/log/ooni/lepidopter-update.log update --watch
TimeoutStartSec=300
Restart=on-failure

[Install]
WantedBy=multi-user.target
""".format(SCRIPT_INSTALL_PATH)

PUBLIC_KEY_PATH = "/opt/ooni/lepidopter-update/public.asc"
PUBLIC_KEY = """\
-----BEGIN PGP PUBLIC KEY BLOCK-----
Comment: PGP

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
h+O+8iKVFs758eJDJtr72KlxfhQ=
=zx02
-----END PGP PUBLIC KEY BLOCK-----
"""


class RequestFailed(Exception):
    pass

def get_request(url, follow_redirects=True):
    cmd = ["curl", "-q"]
    if follow_redirects is True:
        cmd.append("-L")
    cmd.append(url)

    tmp_file = tempfile.TemporaryFile()

    try:
        check_call(cmd, stdout=tmp_file)
    except CalledProcessError:
        raise RequestFailed

    tmp_file.seek(0)

    return tmp_file.read()

def get_current_version():
    if not os.path.exists(CURRENT_VERSION_PATH):
        return 0
    with open(CURRENT_VERSION_PATH) as in_file:
        version = in_file.read()
    return int(version)

def get_latest_version():
    version = get_request(UPDATE_BASE_URL + "latest/version")
    return int(version)

class InvalidSignature(Exception):
    pass

class InvalidPublicKey(Exception):
    pass


def verify_file(signature_path, file_path, signer_pk_path):
    tmp_dir = tempfile.mkdtemp()
    tmp_key = os.path.join(tmp_dir, "signing-key.gpg")

    try:
        try:
            check_call(["gpg", "--batch", "--yes", "-o", tmp_key,
                        "--dearmor", signer_pk_path])
        except CalledProcessError:
            raise InvalidPublicKey

        try:
            output = check_output(["gpg", "--batch", "--status-fd", "1",
                                   "--no-default-keyring", "--keyring",
                                   tmp_key, "--trust-model", "always",
                                   "--verify", signature_path, file_path])
        except CalledProcessError:
            raise InvalidSignature

    except Exception as e:
        raise e

    finally:
        shutil.rmtree(tmp_dir)

    return output

class UpdateFailed(Exception):
    pass

def perform_update(version, skip_verification=False):
    try:
        updater = get_request(UPDATE_BASE_URL + "{0}/update.py".format(version))
        updater_path = os.path.join(UPDATER_PATH, "update-{0}.py".format(version))
    except RequestFailed:
        logging.error("Failed to download update file")
        raise UpdateFailed

    if skip_verification is not True:
        try:
            updater_sig = get_request(UPDATE_BASE_URL + "{0}/update.py.asc".format(version))
            updater_sig_path = os.path.join(UPDATER_PATH, "update-{0}.py.asc".format(version))
        except RequestFailed:
            logging.error("Failed to download update file")
            raise UpdateFailed

    with open(updater_path, "w+") as out_file:
        out_file.write(updater)

    if skip_verification is not True:
        with open(updater_sig_path, "w+") as out_file:
            out_file.write(updater_sig)

    if skip_verification is not True:
        try:
            verify_file(updater_sig_path, updater_path, PUBLIC_KEY_PATH)
        except InvalidSignature:
            logging.error("Found an invalid signature. Bailing")
            raise UpdateFailed

    updater = imp.load_source('updater_{0}'.format(version),
                              updater_path)

    try:
        logging.info("Running install script")
        if updater.__version__ != str(version):
            logging.error("There is a version mismatch in the updater file. This could be a sign of a replay attack.")
            raise UpdateFailed
        updater.run()
    except Exception:
        logging.exception("Failed to run the version update script for version {0}".format(version))
        raise UpdateFailed

    current_version_dir = os.path.dirname(CURRENT_VERSION_PATH)
    try:
        os.makedirs(current_version_dir)
    except OSError as ose:
        if ose.errno != errno.EEXIST:
            raise

    # Update the current version number
    with open(CURRENT_VERSION_PATH, "w+") as out_file:
        out_file.write(str(version))

    logging.info("Updated to version {0}".format(version))

def update_to_version(from_version, to_version, skip_verification=False):
    versions = range(from_version + 1, to_version + 1)
    for version in versions:
        try:
            perform_update(version, skip_verification)
        except UpdateFailed:
            logging.error("Failed to update to version {0}".format(version))
            return

def check_for_update(skip_verification=False):
    logging.info("Checking for update")
    current_version = get_current_version()
    try:
        latest_version = get_latest_version()
    except RequestFailed:
        logging.error("Failed to learn the latest version")
        return

    if current_version < latest_version:
        logging.info("Updating {0}->{1}".format(current_version, latest_version))
        update_to_version(current_version, latest_version, skip_verification)
    else:
        logging.info("Already up to date")

class InvalidInterval(Exception):
    pass

def _get_interval(interval):
    """
    Returns the interval in seconds.
    """
    seconds = 0
    INTERVAL_REGEXP = re.compile("(\d+d)?(\d+h)?(\d+m)?")
    m = INTERVAL_REGEXP.match(interval)
    days, hours, minutes = m.groups()

    if days is not None:
        seconds += int(days[:-1]) * 24 * 60 * 60
    if hours is not None:
        seconds += int(hours[:-1]) * 60 * 60
    if minutes is not None:
        seconds += int(minutes[:-1]) * 60

    if seconds == 0:
        try:
            seconds = int(interval)
        except ValueError:
            raise InvalidInterval
    return seconds


def update(args):
    """
    This command fires the updater.
    """
    if args.watch is True:
        seconds = _get_interval(args.interval)
        while True:
            check_for_update(skip_verification=args.skip_verification)
            time.sleep(seconds)
    else:
        check_for_update(skip_verification=args.skip_verification)


def install(args):
    """
    This command installs the updater.
    """
    directories = [
        UPDATER_PATH,
        os.path.dirname(CURRENT_VERSION_PATH)
    ]
    for path in directories:
        try:
            os.makedirs(path)
        except OSError as ose:
            if ose.errno != errno.EEXIST:
                raise

    with open(CURRENT_VERSION_PATH, "w") as out_file:
        out_file.write("0")

    # Copy myself over to the SCRIPT_INSTALL_PATH
    shutil.copyfile(__file__, SCRIPT_INSTALL_PATH)
    os.chmod(SCRIPT_INSTALL_PATH, int('744', 8))

    with open(PUBLIC_KEY_PATH, "w") as out_file:
        out_file.write(PUBLIC_KEY)
    os.chmod(PUBLIC_KEY_PATH, int('644', 8))

    with open(SYSTEMD_SCRIPT_PATH, "w") as out_file:
        out_file.write(SYSTEMD_SCRIPT)

    check_call(["systemctl", "enable", "lepidopter-update"])
    check_call(["systemctl", "start", "lepidopter-update"])

class InvalidLogLevel(Exception):
    pass

def _setup_logging(args):
    log_file = args.log_file

    try:
        log_level = getattr(logging, args.log_level)
    except AttributeError:
        raise InvalidLogLevel()

    logging.basicConfig(filename=log_file, level=log_level, format=LOG_FORMAT)

def _check_user():
    if getpass.getuser() != 'root':
        print("ERROR: this script must be run as root!")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Auto-update system for lepidopter")
    parser.add_argument('--log-file', help="Specify the path to the logfile")
    parser.add_argument('--log-level', help="Specify the loglevel (CRITICAL, ERROR, WARNING, INFO, DEBUG)", default="INFO")

    sub_parsers = parser.add_subparsers()

    parser_update = sub_parsers.add_parser('update')
    parser_update.add_argument('--watch',
                               action='store_true',
                               help="Keep watching for changes in version and automatically update when a new version is available")
    parser_update.add_argument('--interval', default='6h')
    parser_update.add_argument('--skip-verification',
                               action='store_true',
                               help="Skip key verification (DANGER USE ONLY FOR TESTING))")
    parser_update.set_defaults(func=update)

    parser_install = sub_parsers.add_parser('install')
    parser_install.set_defaults(func=install)

    args = parser.parse_args()
    _setup_logging(args)
    _check_user()
    args.func(args)


if __name__ == "__main__":
    main()
