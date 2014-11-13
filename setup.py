#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ooni import __version__, __author__
import os
import sys
import tempfile
from ConfigParser import SafeConfigParser

from os.path import join as pj
from setuptools import setup
from setuptools.command.install import install as _st_install


class install(_st_install):
    def gen_config(self, share_path):
        config_file = pj(tempfile.mkdtemp(), "ooniprobe.conf.sample")
        o = open(config_file, "w+")
        with open("data/ooniprobe.conf.sample") as f:
            for line in f:
                if "/usr/share" in line:
                    line = line.replace("/usr/share", share_path)
                o.write(line)
        o.close()
        return config_file

    def set_data_files(self, share_path):
        for root, dirs, file_names in os.walk('data/'):
            files = []
            for file_name in file_names:
                if file_name.endswith('.pyc'):
                    continue
                elif file_name.endswith('.dat') and \
                        file_name.startswith('Geo'):
                    continue
                elif file_name == "ooniprobe.conf.sample":
                    files.append(self.gen_config(share_path))
                    continue
                files.append(pj(root, file_name))
            self.distribution.data_files.append(
                [
                    pj(share_path, 'ooni', root.replace('data/', '')),
                    files
                ]
            )
        settings = SafeConfigParser()
        settings.set("directories", "data_dir",
                     os.path.join(share_path, "ooni"))
        with open("ooni/settings.ini", "w+") as fp:
            settings.write(fp)

    def run(self):
        share_path = os.path.abspath(pj(self.prefix, 'share'))
        self.set_data_files(share_path)
        self.do_egg_install()


install_requires = []
dependency_links = []
data_files = []
packages = [
    'ooni',
    'ooni.api',
    'ooni.deckgen',
    'ooni.deckgen.processors',
    'ooni.kit',
    'ooni.nettests',
    'ooni.nettests.manipulation',
    'ooni.nettests.experimental',
    'ooni.nettests.scanning',
    'ooni.nettests.blocking',
    'ooni.nettests.third_party',
    'ooni.report',
    'ooni.resources',
    'ooni.templates',
    'ooni.tests',
    'ooni.utils'
]

with open('requirements.txt') as f:
    for line in f:
        if line.startswith("#"):
            continue
        if line.startswith('https'):
            dependency_links.append(line)
            continue
        install_requires.append(line)

with open('README.rst') as f:
    readme = f.read()

with open('ChangeLog.rst') as f:
    changelog = f.read()

setup(
    name="ooniprobe",
    version=__version__,
    author=__author__,
    author_email="ooni-dev@torproject.org",
    description="Network Interference detection tool.",
    long_description=readme + '\n\n' + changelog,
    license='BSD 2 clause',
    url="https://ooni.torproject.org/",
    package_dir={'ooni': 'ooni'},
    data_files=data_files,
    packages=packages,
    include_package_data=True,
    scripts=["bin/oonideckgen", "bin/ooniprobe",
             "bin/oonireport", "bin/ooniresources"],
    dependency_links=dependency_links,
    install_requires=install_requires,
    cmdclass={"install": install},
    classifiers=(
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Framework :: Twisted",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Telecommunications Industry",
        "License :: OSI Approved :: BSD License"
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2 :: Only",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX",
        "Operating System :: POSIX :: BSD",
        "Operating System :: POSIX :: BSD :: BSD/OS",
        "Operating System :: POSIX :: BSD :: FreeBSD",
        "Operating System :: POSIX :: BSD :: NetBSD",
        "Operating System :: POSIX :: BSD :: OpenBSD",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Unix",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Security",
        "Topic :: Security :: Cryptography",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Testing",
        "Topic :: Software Development :: Testing :: Traffic Generation",
        "Topic :: System :: Networking :: Monitoring",
    )
)

from subprocess import Popen, PIPE
process = Popen(['ooniresources', '--update-inputs', '--update-geoip'],
                stdout=PIPE, stderr=PIPE)
while process.poll() is None:
    out = process.stdout.read()
    sys.stdout.write(out)
    sys.stdout.flush()
