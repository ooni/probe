#!/usr/bin/env python
#-*- coding: utf-8 -*-

from distutils.core import setup

setup(
    name="ooni-probe",
    version="0.0.8",
    author="Arturo Filastò",
    author_email = "art@torproject.org",
    url="https://ooni.torproject.org/",
    package_dir={'ooni': 'ooni'},
    packages=['ooni', 'ooni.templates', 'ooni.utils'],
    scripts=["bin/ooniprobe"],
    install_requires=open('requirements.txt').readlines(),
    dependency_links=["https://hg.secdev.org/scapy/archive/tip.zip#egg=scapy"]
)
