# ooniprobe - Open Observatory of Network Interference

"The Net interprets censorship as damage and routes around it."
                - John Gilmore; TIME magazine (6 December 1993)

OONI, the Open Observatory of Network Interference, is a global observation
network which aims is to collect high quality data using open methodologies,
using Free and Open Source Software (FL/OSS) to share observations and data
about the various types, methods, and amounts of network tampering in the
world.

# Let's get started with this already!

To run OONI-probe without having to install it you must tell python that it
can import modules from the root of ooni-probe, as well as initialize the
included submodules.

## Getting started

Basic requirements:

  * Git: http://git-scm.com/book/en/Getting-Started-Installing-Git
  * Python >= 2.6: http://www.python.org/download/releases/
  * pip: http://www.pip-installer.org/en/latest/

On debian based systems these can be installed with:

    sudo apt-get install git-core python python-pip python-dev build-essential

The python dependencies required for running ooniprobe are:

  * Tor (>2.2.x): https://torproject.org/
  * Twisted (>12.1.0): https://twistedmatrix.com/trac/
  * PyYAML: http://pyyaml.org/
  * Scapy: http://www.secdev.org/projects/scapy/
      * pypcap: https://code.google.com/p/pypcap/
      * libdnet: https://code.google.com/p/libdnet/
  * txtorcon: https://github.com/meejah/txtorcon
  * txsocksx: https://github.com/hellais/txsocksx

## Install Tor

To get the latest version of Tor you should do the following (from: https://www.torproject.org/docs/debian):

    # put in here the value of lsb_release -c (ex. oneirc for ubuntu 11.10 or squeeze for debian 6.0)
    export DISTRIBUTION="squeeze"
    echo "deb http://deb.torproject.org/torproject.org $DISTRIBUTION main" >> /etc/apt/sources.list
    gpg --keyserver keys.gnupg.net --recv 886DDD89
    gpg --export A3C4F0F979CAA22CDBA8F512EE8CBC9E886DDD89 | sudo apt-key add -
    apt-get update
    apt-get install tor


## Configurating a virtual environment

You are highly recommended to install python packages from inside of a virtual
environment, since pip does not download the packages via SSL and you will need
to install it system wide.

This will require you to have installed virtualenv.

    sudo apt-get install python-virtualenv virtualenvwrapper

To create a new virtual environment do

    mkdir $HOME/.virtualenvs
    mkvirtualenv ooni-probe

You will automatically enter the environment. To re-enter this environment in the future, type:

    workon ooni-probe

For convenience, you may want to add the following to your .bashrc:

    if [ -e ~/ooni-probe/bin ]; then
        export PATH=~/ooni-probe/bin:$PATH
    fi
    if [ -e ~/ooni-probe ]; then
        export PYTHONPATH=$PYTHONPATH:~/ooni-probe
    fi

Add the following to $HOME/.virtualenvs/ooni-probe/bin/postactivate to automatically cd into the working directory upon activation.

    if [ -e ~/ooni-probe ] ; then
        cd ~/ooni-probe
    fi

## Installing ooni-probe

Clone the ooniprobe repository:

    git clone https://git.torproject.org/ooni-probe.git
    cd ooni-probe

Then install OONI with:

    pip install -r requirements.txt

If you are not in a virtualenv you will have to run the above command as root:

    sudo pip install -r requirements.txt

## Install libdnet and pypcap python bindings

It's ideal to install these manually since the ones in debian or ubuntu are not
up to date.

The version of pypcap and libdnet ooniprobe is current tested with are
libdnet-1.12 and pypcap 1.1, any other version should be considered untested.

If you don't already have Subversion installed:

    sudo apt-get install subversion

For libdnet:

    wget https://libdnet.googlecode.com/files/libdnet-1.12.tgz
    tar xzf libdnet-1.12.tgz
    cd libdnet-1.12
    ./configure  && make
    cd python/
    python setup.py install
    cd ../../ && rm -rf libdnet-1.12*

For pypcap:

    git clone https://github.com/hellais/pypcap
    cd pypcap/
    pip install pyrex
    make && make install
    cd ../ && rm -rf pypcap-read-only

## Including your geo data in the test report

Including geografical information on where your probe is located helps us
better assess the value of the test. You can personalize these setting from
inside of ooniprobe.conf

If you wish to include geografical data in the test report, you will have to go
to the data/ directory and run:

    make geoip

Then edit your ooniprobe.conf to point to the absolute path of where the data/
directory is located for example:

    geoip_data_dir: /home/your_user/ooni-probe/data/

## Running some tests

To see the possible command line options run:

    ./bin/ooniprobe --help 

For interesting tests to run look in the nettests/core/ directory.

To run a test you can do so with:

    ./bin/ooniprobe -o report_file_name path/to/test.py

Normally tests take options, you can see them with:

    ./bin/ooniprobe -o report_file_name path/to/test.py --help

## Configuration

By default ooniprobe will not include personal identifying information in the
test result, nor create a pcap file. This behavior can be personalized by
editing your ooniprobe.conf configuration file.


