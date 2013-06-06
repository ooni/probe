#!/usr/bin/env python
#-*- coding: utf-8 -*-

from setuptools import setup

import versioneer
versioneer.versionfile_source = 'ooni/_version.py'
versioneer.versionfile_build = 'ooni/_version.py'
versioneer.tag_prefix = 'v'
versioneer.parentdir_prefix = 'ooni'

install_requires = [
    'txsocksx>=0.0.2',
    'scapy>=2.2.0',
    'dnspython>=1.10.0',
    'parsley>1.0',
]

dependency_links = [
    'https://people.torproject.org/~ioerror/src/mirrors/ooniprobe'
]

with open('requirements.txt') as f:
    for line in f:
        if line.startswith("#") or line.startswith('http'):
            continue
        install_requires.append(line)

setup(
    name="ooni-probe",
    description="OONI network censorsorship detection client and network \
test-writing framework",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    author="The Tor Project, Inc",
    maintainer_email = "art@torproject.org",
    url="https://ooni.torproject.org/",
    license="BSD License",
    package_dir={'ooni': 'ooni'},
    packages=['ooni', 'ooni.templates', 'ooni.utils'],
    scripts=["bin/ooniprobe"],
    dependency_links=dependency_links,
    install_requires=install_requires,
    platforms="Linux, BSD, OSX, Windows",
    ## gitweb.torproject.org doesn't have an easy way to point to the .zip
    ## of the latest tag, so we'll have to fill this in later:
    download_url="",
    classifiers=[
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
        "Operating System :: Microsoft :: Windows",
        "Operating System :: Microsoft :: Windows :: Windows 7",
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
    ]
)
