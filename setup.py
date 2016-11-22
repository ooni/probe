"""
ooniprobe: a network interference detection tool
================================================

.. image:: https://travis-ci.org/TheTorProject/ooni-probe.png?branch=master
    :target: https://travis-ci.org/TheTorProject/ooni-probe

.. image:: https://coveralls.io/repos/TheTorProject/ooni-probe/badge.png
    :target: https://coveralls.io/r/TheTorProject/ooni-probe

___________________________________________________________________________

.. image:: https://ooni.torproject.org/images/ooni-header-mascot.png
    :target: https:://ooni.torproject.org/

OONI, the Open Observatory of Network Interference, is a global observation
network which aims is to collect high quality data using open methodologies,
using Free and Open Source Software (FL/OSS) to share observations and data
about the various types, methods, and amounts of network tampering in the
world.

Read this before running ooniprobe!
-----------------------------------

Running ooniprobe is a potentially risky activity. This greatly depends on the
jurisdiction in which you are in and which test you are running. It is
technically possible for a person observing your internet connection to be
aware of the fact that you are running ooniprobe. This means that if running
network measurement tests is something considered to be illegal in your country
then you could be spotted.

Furthermore, ooniprobe takes no precautions to protect the install target machine
from forensics analysis. If the fact that you have installed or used ooni
probe is a liability for you, please be aware of this risk.


Setup ooniprobe
-------------------

To install ooniprobe you will need the following dependencies:

    * python
    * python-dev
    * python-setuptools
    * build-essential
    * libdumbnet1
    * python-dumbnet
    * python-libpcap
    * tor
    * libgeoip-dev
    * libpcap0.8-dev
    * libssl-dev
    * libffi-dev
    * libdumbnet-dev


On debian based systems this can generally be done by running:

.. code:: bash

    sudo apt-get install -y build-essential libdumbnet-dev libpcap-dev libgeoip-dev libffi-dev python-dev python-pip

When you got them run:

.. code:: bash

    sudo pip install ooniprobe

Using ooniprobe
---------------

It is recommended that you start the ooniprobe-agent system daemon that will
expose a localhost only Web UI and automatically run tests for you.

This can be done with:

.. code:: bash

    ooniprobe-agent start


Then connect to the local web interface on http://127.0.0.1:8842/

Have fun!
"""

from __future__ import print_function

import os
import errno
import tempfile
from glob import glob

from ConfigParser import SafeConfigParser

from os.path import join as pj
from setuptools import setup
from setuptools.command.install import install as InstallCommand
from subprocess import check_call

from ooni import __version__, __author__

CLASSIFIERS = """\
Development Status :: 5 - Production/Stable
Environment :: Console
Framework :: Twisted
Intended Audience :: Developers
Intended Audience :: Education
Intended Audience :: End Users/Desktop
Intended Audience :: Information Technology
Intended Audience :: Science/Research
Intended Audience :: Telecommunications Industry
License :: OSI Approved :: BSD License
Programming Language :: Python
Programming Language :: Python :: 2
Programming Language :: Python :: 2 :: Only
Programming Language :: Python :: 2.6
Programming Language :: Python :: 2.7
Operating System :: MacOS :: MacOS X
Operating System :: POSIX
Operating System :: POSIX :: BSD
Operating System :: POSIX :: BSD :: BSD/OS
Operating System :: POSIX :: BSD :: FreeBSD
Operating System :: POSIX :: BSD :: NetBSD
Operating System :: POSIX :: BSD :: OpenBSD
Operating System :: POSIX :: Linux
Operating System :: Unix
Topic :: Scientific/Engineering :: Information Analysis
Topic :: Security
Topic :: Security :: Cryptography
Topic :: Software Development :: Libraries :: Application Frameworks
Topic :: Software Development :: Libraries :: Python Modules
Topic :: Software Development :: Testing
Topic :: Software Development :: Testing :: Traffic Generation
Topic :: System :: Networking :: Monitoring
"""


def is_lepidopter():
    return os.path.exists('/etc/default/lepidopter')


def is_updater_installed():
    return os.path.exists('/etc/lepidopter-update/version')


def install_lepidopter_update():
    check_call(["data/lepidopter-update.py", "install"])


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as ose:
        if ose.errno != errno.EEXIST:
            raise

class OoniInstall(InstallCommand):
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

    def set_data_files(self, prefix):
        share_path = pj(prefix, 'share')
        if prefix.startswith("/usr"):
            var_path = "/var/lib/"
        else:
            var_path = pj(prefix, 'var', 'lib')

        self.distribution.data_files.append(
            (
                pj(share_path, 'ooni', 'decks-available'),
                glob('data/decks/*')
            )
        )
        settings = SafeConfigParser()
        settings.add_section("directories")
        settings.set("directories", "usr_share",
                     os.path.join(share_path, "ooni"))
        settings.set("directories", "var_lib",
                     os.path.join(var_path, "ooni"))
        settings.set("directories", "etc",
                     os.path.join(var_path, "ooni"))
        with open("ooni/settings.ini", "w+") as fp:
            settings.write(fp)

        mkdir_p(pj(var_path, 'ooni'))
        mkdir_p(pj(share_path, 'ooni'))
        mkdir_p(pj(share_path, 'ooni', 'decks-available'))

    def pre_install(self):
        prefix = os.path.abspath(self.prefix)
        self.set_data_files(prefix)

    def run(self):
        self.pre_install()
        self.do_egg_install()
        if is_lepidopter() and not is_updater_installed():
            print("Lepidopter now requires that ooniprobe is installed via the "
                 "updater")
            print("Let me install the auto-updater for you and we shall use that "
                  "for updates in the future.")
            install_lepidopter_update()

def setup_package():
    setup_requires = []
    install_requires = []
    dependency_links = []
    data_files = []
    packages = [
        'ooni',
        'ooni.agent',
        'ooni.common',
        'ooni.contrib',
        'ooni.contrib.dateutil',
        'ooni.contrib.dateutil.tz',
        'ooni.deck',
        'ooni.kit',
        'ooni.nettests',
        'ooni.nettests.manipulation',
        'ooni.nettests.experimental',
        'ooni.nettests.scanning',
        'ooni.nettests.blocking',
        'ooni.nettests.third_party',
        'ooni.scripts',
        'ooni.templates',
        'ooni.tests',
        'ooni.ui',
        'ooni.ui.web',
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

    metadata = dict(
        name="ooniprobe",
        version=__version__,
        author=__author__,
        author_email="contact@openobservatory.org",
        description="Network measurement tool for"
                    "identifying traffic manipulation and blocking.",
        long_description=__doc__,
        license='BSD 2 clause',
        url="https://ooni.torproject.org/",
        package_dir={'ooni': 'ooni'},
        data_files=data_files,
        packages=packages,
        include_package_data=True,
        dependency_links=dependency_links,
        install_requires=install_requires,
        setup_requires=setup_requires,
        zip_safe=False,
        entry_points={
            'console_scripts': [
                'ooniresources = ooni.scripts.ooniresources:run',  # This is deprecated
                'oonideckgen = ooni.scripts.oonideckgen:run',  # This is deprecated

                'ooniprobe = ooni.scripts.ooniprobe:run',
                'oonireport = ooni.scripts.oonireport:run',
                'ooniprobe-agent = ooni.scripts.ooniprobe_agent:run'
            ]
        },
        cmdclass={
            "install": OoniInstall
        },
        classifiers=[c for c in CLASSIFIERS.split('\n') if c]
    )

    setup(**metadata)

if __name__ == "__main__":
    setup_package()
