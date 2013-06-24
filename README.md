# ooniprobe - Open Observatory of Network Interference

"The Net interprets censorship as damage and routes around it."
                - John Gilmore; TIME magazine (6 December 1993)

OONI, the Open Observatory of Network Interference, is a global observation
network which aims is to collect high quality data using open methodologies,
using Free and Open Source Software (FL/OSS) to share observations and data
about the various types, methods, and amounts of network tampering in the
world.

ooniprobe is the first program that users run to probe their network and to
collect data for the OONI project. Are you interested in testing your network
for signs of surveillance and censorship? Do you want to collect data to share
with others, so that you and others may better understand your network? If so,
please read this document and we hope ooniprobe will help you to gather
network data that will assist you with your endeavors!

## Getting started with ooniprobe is easy (with Vagrant)

0) [Install Vagrant](http://downloads.vagrantup.com/) and [Install Virtualbox](https://www.virtualbox.org/wiki/Downloads)

0.1)

On OSX:

If youd don't have it install homebrew http://mxcl.github.io/homebrew/

```
brew install git
```

On debian/ubuntu:

```
sudo apt-get install git
```

1) Open a Terminal and run:

```
git clone https://git.torproject.org/ooni-probe.git
cd ooni-probe/
vagrant up
```

2) Login to the box with:

```
vagrant ssh
```

ooniprobe will be installed in `/data/ooniprobe`.

3) You can run tests with:

```
cd /data/ooniprobe/
./bin/ooniprobe nettests/blocking/http_requests.py -f /data/ooniprobe/inputs/input-pack/alexa-top-1k.txt
```

## The easy way to prep your system for running ooniprobe

We believe that ooniprobe runs reasonably well on Debian GNU/Linux wheezy as
well as versions of Ubuntu such as natty and later releases. Running ooniprobe
without installing it is supported with the following commands:

```
git clone https://git.torproject.org/ooni-probe.git
cd ooni-probe
./setup-dependencies.sh
./bin/ooniprobe --asciilulz
```

## Your first network test

We run ooniprobe with a test deck - this is a collection of tests in a single
file that tells ooniprobe how to run and what data to check or process:

```
./bin/ooniprobe -i decks/before_i_commit.testdeck
```

The report output files from the above command will be located in the reports/
directory of the source code checkout. The report output ends with the .yamloo
suffix.

## The details

We haven't actually installed ooniprobe - we just added the ooniprobe python
to your PYTHONPATH. We also installed all of the dependencies with your native
package manager or into a local directory managed by your user.

## ooniprobe requirements explained

Basic system requirements:

  * Git: http://git-scm.com/book/en/Getting-Started-Installing-Git
  * Python >= 2.6: http://www.python.org/download/releases/
  * pip: http://www.pip-installer.org/en/latest/


## The more detailed way follows

On Debian or Ubuntu GNU/Linux based systems these can be installed with:

```
sudo apt-get install git-core python python-pip python-dev build-essential tor tor-geoipdb tcpdump
```

Other packages that may be of interest:

```
libdumbnet1 python-dumbnet python-libpcap python-pypcap python-pcapy python-dnspython
python-virtualenv virtualenvwrapper tor tor-geoipdb
```

The Python dependencies required for running ooniprobe are:

  * Tor (>2.2.x): https://torproject.org/
  * Twisted (>12.1.0): https://twistedmatrix.com/trac/
  * PyYAML: http://pyyaml.org/
  * Scapy: http://www.secdev.org/projects/scapy/
      * pypcap: https://code.google.com/p/pypcap/
      * libdnet: https://code.google.com/p/libdnet/
  * txtorcon: https://github.com/meejah/txtorcon
  * txsocksx: https://github.com/hellais/txsocksx

## Install Tor

Install the latest version of Tor for your platform:

[Download Tor](https://www.torproject.org/download/download.html)

## Configurating a virtual environment

You are highly recommended to install python packages from inside of a virtual
environment, since pip does not download the packages via SSL and you will need
to install it system wide.

This will require you to have installed virtualenv.

```
sudo apt-get install python-virtualenv virtualenvwrapper
```

To create a new virtual environment do

```
mkdir $HOME/.virtualenvs
mkvirtualenv ooni-probe
```

You will automatically enter the environment. To re-enter this environment in the future, type:

```
workon ooni-probe
```

For convenience, you may want to add the following to your .bashrc:

```
if [ -e ~/ooni-probe/bin ]; then
    export PATH=~/ooni-probe/bin:$PATH
fi
if [ -e ~/ooni-probe ]; then
    export PYTHONPATH=$PYTHONPATH:~/ooni-probe
fi
```

Add the following to $HOME/.virtualenvs/ooni-probe/bin/postactivate to automatically cd into the working directory upon activation.

```
if [ -e ~/ooni-probe ] ; then
    cd ~/ooni-probe
fi
```

## Installing ooni-probe

Clone the ooniprobe repository:

```
git clone https://git.torproject.org/ooni-probe.git
cd ooni-probe
```

Then install OONI with:

```
pip install -r requirements.txt
```

If you are not in a virtualenv you will have to run the above command as root:

```
sudo pip install -r requirements.txt
```

## Install libdnet and pypcap python bindings

It's ideal to install these manually since the ones in debian or ubuntu are not
up to date.

The version of pypcap and libdnet ooniprobe is current tested with are
libdnet-1.12 and pypcap 1.1, any other version should be considered untested.

If you don't already have Subversion installed:

```
sudo apt-get install subversion
```

For libdnet:

```
wget https://libdnet.googlecode.com/files/libdnet-1.12.tgz
tar xzf libdnet-1.12.tgz
cd libdnet-1.12
./configure  && make
cd python/
python setup.py install
cd ../../ && rm -rf libdnet-1.12*
```

For pypcap:

```
git clone https://github.com/hellais/pypcap
cd pypcap/
pip install pyrex
make && make install
cd ../ && rm -rf pypcap-read-only
```

## Including your geo data in the test report

Including geografical information on where your probe is located helps us
better assess the value of the test. You can personalize these setting from
inside of ooniprobe.conf

If you wish to include geografical data in the test report, you will have to go
to the data/ directory and run:

```
make geoip
```

Then edit your ooniprobe.conf to point to the absolute path of where the data/
directory is located for example:

```
geoip_data_dir: /home/your_user/ooni-probe/data/
```

## Running some tests

To see the possible command line options run:

```
./bin/ooniprobe --help 
```

For interesting tests to run look in the nettests/core/ directory.

To run a test you can do so with:

```
./bin/ooniprobe -o report_file_name path/to/test.py
```

Normally tests take options, you can see them with:

```
./bin/ooniprobe -o report_file_name path/to/test.py --help
```

## Configuration

By default ooniprobe will not include personal identifying information in the
test result, nor create a pcap file. This behavior can be personalized by
editing your ooniprobe.conf configuration file.

## Setting capabilities on your virtualenv python binary

If your distributation supports capabilities you can avoid needing to run OONI as root:

```
setcap cap_net_admin,cap_net_raw+eip /path/to/your/virtualenv's/python
```

