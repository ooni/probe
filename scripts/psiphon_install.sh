#!/bin/sh

#FIXME remove x
set -ex

PSIPHON_PATH=$HOME/test
PSIPHON_PYCLIENT_PATH=$PSIPHON_PATH/psiphon-circumvention-system/pyclient

echo "installing dependencies"
# FIXME: check if hg command exits and if not bail out?
sudo apt-get install -y mercurial
echo "cloning psiphon repository"
cd $PSIPHON_PATH
hg clone https://bitbucket.org/psiphon/psiphon-circumvention-system
echo "psiphon repository cloned"

# optional, compile their ssh
echo "compiling psiphon ssh"
cd psiphon-circumvention-system/Server/3rdParty/openssh-5.9p1/
./configure
make
mv ssh ../../../pyclient/
make clean
echo "psiphon ssh compiled"

# check if we are in a virtualenv, create it otherwise
echo "checking virtualenv"
if [ python -c 'import sys; print hasattr(sys, "real_prefix")'  = "False"];then
    # we are not in a virtualenv
    # create a virtualenv
    # FIXME: assuming debian version will have secure pip/virtualenv
    sudo apt-get -y install python-virtualenv

    if [ ! -f $HOME/.virtualenvs/ooniprobe/bin/activate ]; then
      # Set up the virtual environment
      mkdir -p $HOME/.virtualenvs
      virtualenv $HOME/.virtualenvs/ooniprobe
      source $HOME/.virtualenvs/ooniprobe/bin/activate
    else
      source $HOME/.virtualenvs/ooniprobe/bin/activate
    fi
fi
echo "virtualenv activated"

# create psi_client.dat
echo "creating servers data file"
echo "installing dependencies to create servers data file"
pip install -v --timeout 60  wget
cd /tmp
cat <<EOF > psi_generate_dat.py
#!/usr/bin/env python

import wget
import os
import json

# Delete 'server_list' if exists
if os.path.exists("server_list"):
    # os.remove("server_list")
    # os.rename("server_list", "server_list")
    pass
else:
    # Download 'server_list'
    url ="https://psiphon3.com/server_list"
    wget.download(url)

# convert server_list to psi_client.dat
dat = {}
dat["propagation_channel_id"] = "FFFFFFFFFFFFFFFF"
dat["sponsor_id"] = "FFFFFFFFFFFFFFFF"
dat["servers"] = json.load(open('server_list'))['data'].split()
json.dump(dat, open('psi_client.dat', 'w'))
EOF

chmod +x psi_generate_dat.py 
./psi_generate_dat.py
echo "serers data file created"
mv psi_client.dat $PSIPHON_PYCLIENT_PATH


echo "[+] Installing all of the Python dependency requirements with pip in your virtualenv!";
pip install -v --timeout 60  jsonpickle pexpect

# run psiphon
# cd $PSIPHON_PYCLIENT_PATH
# python psi_client.py
