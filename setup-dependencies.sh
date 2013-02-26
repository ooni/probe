#!/bin/bash

# Discover our Distro release
RELEASE="`lsb_release -c|cut -f 2`";
TOR_DEB_REPO="deb.torproject.org/torproject.org";

echo "sudo is annoying, tell us your password once and sudo won't annoy you for the rest of this process...";
sudo echo "if you read this, we won't ask for your password again during this process unless something goes wrong";

# This is for Ubuntu's natty
if [ $RELEASE = "natty" ] || [ $RELEASE = "wheezy" ]; then
  # Add Tor repo
  HAVE_GPG_KEY="`sudo apt-key finger|grep 'A3C4 F0F9 79CA A22C DBA8  F512 EE8C BC9E 886D DD89'|head -n 1`";
  if [ -z "$HAVE_GPG_KEY" ]; then
    echo "It appears that you do not have the torproject.org Debian repository key installed; installing it...";
    cat apt.key | sudo apt-key add -;
  else
    echo "It appears that you have the torproject.org Debian repository key installed!";
  fi

  HAVE_TOR_REPO="`grep deb.torproject.org/torproject.org /etc/apt/sources.list /etc/apt/sources.list.d/* 2>&1|grep torproject|head -n 1`";
  if [ -z "$HAVE_TOR_REPO" ]; then
    echo "It appears that you do not have the torproject.org Debian repository installed; installing it...";
    sudo apt-add-repository "deb $TOR_DEB_REPO $RELEASE main";
  else
    echo "It appears that you have the torproject.org Debian repository installed!";
  fi

  # Install the basic packages to get pip ready to roll
  echo "Updating OS package list...";
  sudo apt-get update 2>&1 > /dev/null;
  echo "Installing packages for your system...";
  sudo apt-get install git-core python python-pip python-dev build-essential libdumbnet1 python-dumbnet python-libpcap python-pypcap python-dnspython python-virtualenv virtualenvwrapper tor tor-geoipdb;

  if [ ! -f ~/.virtualenvs/ooniprobe/bin/activate ]; then
    # Set up the virtual environment
    mkdir ~/.virtualenvs/
    virtualenv ~/.virtualenvs/ooniprobe
    source ~/.virtualenvs/ooniprobe/bin/activate
  else
    source ~/.virtualenvs/ooniprobe/bin/activate
  fi

  echo "Installing all of the Python dependency requirements with pip!";
  # Install all of the out of package manager dependencies
  pip install -v --timeout 60 -r requirements.txt;
  if [ $? != 0 ]; then
    echo "It appears that pip is having issues installing our Python dependency requirements, we'll try again!";
    pip install -v --timeout 60 -r requirements.txt;
    if [ $? != 0 ]; then
      echo "It appears that pip is unable to satisfy our requirements - please run the following command:";
      echo "   pip install -v --timeout 60 -r requirements.txt   ";
      exit 1;
    fi
  fi

  echo "Adding a symlink to your ooni-probe source code checkout...";
  ln -s `pwd` ~/ooni-probe;
  echo "Adding a default ooniprobe.conf file...";
  cp -v ooniprobe.conf.sample ooniprobe.conf
  echo "Creating reports/ directory to store output from ooniprobe...";
  mkdir `pwd`/reports/

  # Allow ooniprobe to run, if all above went well, we hope!
  export PYTHONPATH=$PYTHONPATH:"`pwd`";
  export PATH=$PATH:"`pwd`";
  echo "Please add the following to your respective shell config files:";
  echo ;
  echo "  if [ -e ~/ooni-probe/bin ]; then";
  echo '    export PATH=~/ooni-probe/bin:$PATH';
  echo "  fi";
  echo "  if [ -e ~/ooni-probe ]; then";
  echo '    export PYTHONPATH=$PYTHONPATH:~/ooni-probe';
  echo "  fi";
  echo ;

else

  echo "It appears that you are using an unsupported OS - please tell us";
  echo "by filing a bug: https://trac.torproject.org/projects/tor/newticket";

fi

