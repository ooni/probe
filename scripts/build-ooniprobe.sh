#!/bin/bash
set -e
cd ../
python setup.py sdist
cd dist/
py2dsc ooniprobe-*.tar.gz
cd deb_dist/ooniprobe-*
rm -rf debian/
cp -rf ../../../debian ./debian
debuild
