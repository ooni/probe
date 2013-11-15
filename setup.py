#!/usr/bin/env python
#-*- coding: utf-8 -*-

from ooni import __version__
import os
from os.path import join as pj
import sys
from setuptools import setup

dependency_links = [
    'https://people.torproject.org/~ioerror/src/mirrors/ooniprobe'
]

usr_share_path = '/usr/share/ooni'
# If this is true then it means we are in a virtualenv
if hasattr(sys, 'real_prefix'):
    usr_share_path = pj(sys.prefix, 'share', 'ooni')
    with open(pj('data', 'ooniprobe.conf.sample.new'), 'w+') as w:
        with open(pj('data', 'ooniprobe.conf.sample')) as f:
            for line in f:
                if line.startswith('    data_dir: /usr/share/ooni'):
                    w.write('    data_dir: %s\n' % usr_share_path)
                else:
                    w.write(line)
    os.rename(pj('data', 'ooniprobe.conf.sample.new'),
              pj('data', 'ooniprobe.conf.sample'))

data_files = []
for root, dirs, file_names in os.walk('data/'):
    files = []
    for file_name in file_names:
        if not file_name.endswith('.pyc'):
            files.append(pj(root, file_name))
    data_files.append([pj(usr_share_path, root.replace('data/', '')), files])

install_requires = []
with open('requirements.txt') as f:
    for line in f:
        if line.startswith("#") or line.startswith('http'):
            continue
        install_requires.append(line)

setup(
    name="ooniprobe",
    version=__version__,
    author="Open Observatory of Network Interference",
    author_email = "ooni-dev@torproject.org",
    url="https://ooni.torproject.org/",
    package_dir={'ooni': 'ooni'},
    data_files=data_files,
    packages=['ooni', 'ooni.api', 'ooni.kit', 
        'ooni.nettests', 'ooni.nettests.manipulation', 
        'ooni.nettests.experimental', 'ooni.nettests.scanning',
        'ooni.nettests.blocking',
        'ooni.nettests.third_party',
        'ooni.templates', 'ooni.tests', 'ooni.utils'],

    scripts=["bin/ooniprobe"],
    dependency_links=dependency_links,
    install_requires=install_requires
)
