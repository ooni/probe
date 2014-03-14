#!/usr/bin/env python
#-*- coding: utf-8 -*-

from ooni import __version__, __author__
import urllib2
import os
import gzip
from os.path import join as pj
import sys
from setuptools import setup

def download_geoip_files(dst):
    urls = [
        'http://www.maxmind.com/download/geoip/database/asnum/GeoIPASNum.dat.gz',
        'http://geolite.maxmind.com/download/geoip/database/GeoLiteCountry/GeoIP.dat.gz',
        'http://geolite.maxmind.com/download/geoip/database/GeoLiteCity.dat.gz'
    ]
    if not os.path.exists(dst):
        os.makedirs(dst)
    for url in urls:
        target_gz_file = pj(dst, os.path.basename(url))
        target_file = target_gz_file.replace('.gz', '')

        if os.path.isfile(target_file):
            print "%s already exists. Skipping." % target_file
            continue

        print "Downloading %s" % url
        response = urllib2.urlopen(url)

        CHUNK = 4 * 1024
        with open(target_gz_file, 'w+') as f:
            while True:
                chunk = response.read(CHUNK)
                if not chunk: break
                f.write(chunk)
        
        with open(target_file, 'w+') as f:
            gf = gzip.open(target_gz_file, 'rb')
            while True:
                chunk = gf.read(CHUNK)
                if not chunk: break
                f.write(chunk)
            gf.close()

        os.unlink(target_gz_file)

usr_share_path = '/usr/share'
# If this is true then it means we are in a virtualenv
# therefore we should not place our data files inside /usr/share/ooni, but
# place them inside the virtual env system prefix.
if hasattr(sys, 'real_prefix'):
    usr_share_path = os.path.abspath(pj(sys.prefix, 'share'))

download_geoip_files(pj(usr_share_path, 'GeoIP'))

install_requires = []
dependency_links = []
data_files = []

for root, dirs, file_names in os.walk('data/'):
    files = []
    for file_name in file_names:
        if file_name.endswith('.pyc'):
            continue
        elif file_name.endswith('.dat') and \
                file_name.startswith('Geo'):
            continue
        files.append(pj(root, file_name))
    data_files.append([pj(usr_share_path, 'ooni', root.replace('data/', '')), files])

with open('requirements.txt') as f:
    for line in f:
        if line.startswith("#"):
            continue
        if line.startswith('https'):
            dependency_links.append(line)
            continue
        install_requires.append(line)

setup(
    name="ooniprobe",
    version=__version__,
    author=__author__,
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
