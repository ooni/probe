#!/bin/bash

PSIPHON_PATH=$HOME
PSIPHON_PYCLIENT_PATH=$PSIPHON_PATH/psiphon-circumvention-system/pyclient

sudo apt-get install mercurial
cd $PSIPHON_PATH
hg clone https://bitbucket.org/psiphon/psiphon-circumvention-system
# optional, compile their ssh
#cd psiphon-circumvention-system/Server/3rdParty/openssh-5.9p1/
#./configure
#make
#cp ssh ../../../pyclient/
#cd $PSIPHON_PATH

# create psi_client.dat
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
    url ="https://psiphon3.com/server_list'
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
cp psi_client.dat $PSIPHON_PYCLIENT_PATH

# assuming to be inside a virtualenv
pip install jsonpickle pexpect

# run psiphon
# cd $PSIPHON_PYCLIENT_PATH
# psi_client.py
