#!/usr/bin/env python
#-*- coding: utf-8 -*-

from setuptools import setup

install_requires = [
    'txsocksx>=0.0.2',
    'scapy>=2.2.0',
    'dnspython>=1.10.0',
    'parsley>1.0',
    'pypcap>=1.1.1'
]

dependency_links = [
    'https://people.torproject.org/~ioerror/src/mirrors/ooniprobe',
    'https://github.com/hellais/pypcap/archive/v1.1.1.tar.gz#egg=pypcap-1.1.1'
]

with open('requirements.txt') as f:
    for line in f:
        if line.startswith("#") or line.startswith('http'):
            continue
        install_requires.append(line)

setup(
    name="ooni-probe",
    version="0.0.11",
    author="Arturo Filastò",
    author_email = "art@torproject.org",
    url="https://ooni.torproject.org/",
    package_dir={'ooni': 'ooni'},
    packages=['ooni', 'ooni.templates', 'ooni.utils'],
    scripts=["bin/ooniprobe"],
    dependency_links=dependency_links,
    install_requires=install_requires,
)
