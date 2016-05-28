import shutil
import string
import random
import os
from datetime import datetime

import gzip
from zipfile import ZipFile

from ooni import errors


class Storage(dict):
    """
    A Storage object is like a dictionary except `obj.foo` can be used
    in addition to `obj['foo']`.

        >>> o = Storage(a=1)
        >>> o.a
        1
        >>> o['a']
        1
        >>> o.a = 2
        >>> o['a']
        2
        >>> del o.a
        >>> o.a
        None
    """

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            return None

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError, k:
            raise AttributeError(k)

    def __repr__(self):
        return '<Storage ' + dict.__repr__(self) + '>'

    def __getstate__(self):
        return dict(self)

    def __setstate__(self, value):
        for (k, v) in value.items():
            self[k] = v


def checkForRoot():
    if os.getuid() != 0:
        raise errors.InsufficientPrivileges


def randomSTR(length, num=True):
    """
    Returns a random all uppercase alfa-numerical (if num True) string long length
    """
    chars = string.ascii_uppercase
    if num:
        chars += string.digits
    return ''.join(random.choice(chars) for x in range(length))


def randomstr(length, num=True):
    """
    Returns a random all lowercase alfa-numerical (if num True) string long length
    """
    chars = string.ascii_lowercase
    if num:
        chars += string.digits
    return ''.join(random.choice(chars) for x in range(length))


def randomStr(length, num=True):
    """
    Returns a random a mixed lowercase, uppercase, alfanumerical (if num True)
    string long length
    """
    chars = string.ascii_lowercase + string.ascii_uppercase
    if num:
        chars += string.digits
    return ''.join(random.choice(chars) for x in range(length))

def generate_filename(test_details, prefix=None, extension=None):
    """
    Returns a filename for every test execution.

    It's used to assure that all files of a certain test have a common basename but different
    extension.
    """
    LONG_DATE = "%Y-%m-%d %H:%M:%S"
    SHORT_DATE = "%Y-%m-%dT%H%M%SZ"

    kwargs = {}
    filename_format = ""
    if prefix is not None:
        kwargs["prefix"] = prefix
        filename_format += "{prefix}-"
    filename_format += "{test_name}-{timestamp}"
    if extension is not None:
        kwargs["extension"] = extension
        filename_format += ".{extension}"
    kwargs['test_name']  = test_details['test_name']
    kwargs['timestamp'] = datetime.strptime(test_details['test_start_time'],
                                            LONG_DATE).strftime(SHORT_DATE)
    return filename_format.format(**kwargs)

def sanitize_options(options):
    """
    Strips all possible user identifying information from the ooniprobe test
    options.
    Currently only strips leading directories from filepaths.
    """
    sanitized_options = []
    for option in options:
        option = os.path.basename(option)
        sanitized_options.append(option)
    return sanitized_options


def unzip(filename, dst):
    assert filename.endswith('.zip')
    dst_path = os.path.join(
        dst,
        os.path.basename(filename).replace(".zip", "")
    )
    with open(filename) as zfp:
        zip_file = ZipFile(zfp)
        zip_file.extractall(dst_path)
    return dst_path


def gunzip(filename, dst):
    assert filename.endswith(".gz")
    dst_path = os.path.join(
        dst,
        os.path.basename(filename).replace(".gz", "")
    )
    with open(dst_path, "w+") as fw:
        gzip_file = gzip.open(filename)
        shutil.copyfileobj(gzip_file, fw)
        gzip_file.close()


def get_ooni_root():
    script = os.path.join(__file__, '..')
    return os.path.dirname(os.path.realpath(script))
