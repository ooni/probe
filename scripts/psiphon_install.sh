#!/bin/sh

set -e

PSIPHON_HOME_PATH=$HOME
PSIPHON_PYCLIENT_PATH=$PSIPHON_HOME_PATH/psiphon-circumvention-system/pyclient
PSIPHON_SSH_PATH=$PSIPHON_HOME_PATH/psiphon-circumvention-system/Server/3rdParty/openssh-5.9p1
PSIPHON_REPO_URL=https://bitbucket.org/psiphon/psiphon-circumvention-system#af438ec2c16c
VIRTUALENVS_PATH=$HOME/.virtualenvs
OONI_VIRTUALENV_PATH=$VIRTUALENVS_PATH/ooniprobe

mkdir -p $PSIPHON_HOME_PATH

command_exists() {
  command -v "$@" > /dev/null 2>&1
}

user="$(id -un 2>/dev/null || true)"

sh_c='sh -c'

if [ "$user" != 'root' ]; then
  if command_exists sudo; then
    sh_c='sudo sh -c -E'
    echo "[D] using sudo"
  elif command_exists su; then
    sh_c='su -c --preserve-environment'
    echo "[D] using su"
  else
    echo >&2 'Error: this installer needs the ability to run commands as root.'
    echo >&2 'We are unable to find either "sudo" or "su" available to make this happen.'
    exit 1
  fi
fi

echo "[D] installing dependencies"
$sh_c "apt-get -y install zlib1g-dev libssl-dev"

if ! command_exists hg; then
  echo "[D] installing mercurial"
  $sh_c "apt-get -y install mercurial"
fi
echo "[D] mercurial installed"

cd $PSIPHON_HOME_PATH
if [ ! -d "psiphon-circumvention-system" ]; then
  echo "[D] cloning psiphon repository"
  hg clone $PSIPHON_REPO_URL
fi

echo "[D] psiphon repository cloned"

# optional, compile their ssh
if [ ! -f "$PSIPHON_PYCLIENT_PATH/ssh" ]; then
    echo "[D] compiling psiphon ssh"
    cd $PSIPHON_SSH_PATH
    ./configure
    make
    mv ssh $PSIPHON_PYCLIENT_PATH
    make clean
    echo "[D] psiphon ssh compiled"
fi

# check if we are in a virtualenv, create it otherwise
echo "[D] checking virtualenv"
if [ `python -c 'import sys; print hasattr(sys, "real_prefix")'` = "False" ]; then
  echo "[D] not in a virtualenv"
  if [ ! -f $OONI_VIRTUALENV_PATH/bin/activate ]; then
    echo "[D] virtualenv not found"
    # create a virtualenv
    # FIXME: assuming debian version will have secure pip/virtualenv
    if ! command_exists virtualenv; then
      echo "[D] installing virtualenv"
      $sh_c "apt-get -y install python-virtualenv"
    else
      echo "[D] virtualenv command found"
    fi
    echo "[D] creating a virtualenv"
    # Set up the virtual environment
    mkdir -p $HOME/.virtualenvs
    virtualenv $OONI_VIRTUALENV_PATH
    . $OONI_VIRTUALENV_PATH/bin/activate
  else
    . $OONI_VIRTUALENV_PATH/bin/activate
  fi
  echo "[D] virtualenv activated"
fi

# create psi_client.dat
echo "[D] creating servers data file"
echo "[D] installing dependencies to create servers data file"
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
echo "[D] servers data file created"
mv psi_client.dat $PSIPHON_PYCLIENT_PATH
rm /tmp/psi_generate_dat.py

echo "[D] installing all of the Python dependency requirements with pip in the virtualenv";
pip install -v --timeout 60  jsonpickle pexpect

echo "You can now run Psiphon: cd ~/psiphon-circumvention-system/pyclient/pyclient;python psi_client.py"
echo "NOTE that if OONI is not installed, you will not be able to run OONI Psiphon test"
