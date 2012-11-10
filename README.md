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

Requirements:

  * Git: http://git-scm.com/book/en/Getting-Started-Installing-Git
  * Python >= 2.6: http://www.python.org/download/releases/
  * pip: http://www.pip-installer.org/en/latest/

On debian based systems these can be installed with:

  apt-get install git-core python python-pip python-dev

The python dependencies required for running ooniprobe are:

  * Twisted
  * Scapy >= 2.2.0
  * txtorcon

They can be installed from the requirements.txt with:

  pip install -r requirements.txt

You are highly recommended to do so from inside of a virtual environment, since
pip does not download the packages via SSL and you will need to install it
system wide.

This will require you to have installed virtualenv.

  apt-get install python-virtualenv

To create a new virtual environment do

  virtualenv env

Then install OONI with:

  pip install -r requirements.txt

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



