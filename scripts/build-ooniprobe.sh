#!/bin/bash
set -e
cd ../
cat data/ooniprobe.conf.sample | sed s/'start_tor: true'/'start_tor: false'/ | sed s/'#socks_port: 8801'/'socks_port: 9050'/ > data/ooniprobe.conf.sample.new
mv data/ooniprobe.conf.sample data/ooniprobe.conf.sample.bak 
mv data/ooniprobe.conf.sample.new data/ooniprobe.conf.sample
python setup.py sdist
cd dist/
py2dsc ooniprobe-*.tar.gz
cd deb_dist/ooniprobe-*
rm -rf debian/
cp -rf ../../../debian ./debian
debuild
cd ../../../
mv data/ooniprobe.conf.sample.bak data/ooniprobe.conf.sample 
