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

  * Twisted (>12.0.0): http://twistedmatrix.com/trac/
  * PyYAML: http://pyyaml.org/
  * Scapy: http://www.secdev.org/projects/scapy/
      * pypcap: http://code.google.com/p/pypcap/
      * libdnet: http://code.google.com/p/libdnet/
  * BeautifulSoup: http://www.crummy.com/software/BeautifulSoup/
  * txtorcon: https://github.com/meejah/txtorcon

### Installing scapy

Unfortunately the version of scapy that is stored on pypi is out of date, this
means that you will have to manually download and install scapy.

This can be done like so:

    wget http://www.secdev.org/projects/scapy/files/scapy-latest.tar.gz
    tar xzf scapy-latest.tar.gz
    cd scapy-*
    python setup.py install

If you are not inside of a virtual env the last command will have to be:

    sudo python setup.py install

### Installing the rest of dependencies

The other dependencies can be installed from the requirements.txt with:

    sudo pip install -r requirements.txt

You are highly recommended to do so from inside of a virtual environment, since
pip does not download the packages via SSL and you will need to install it
system wide.

This will require you to have installed virtualenv.

    sudo apt-get install python-virtualenv

To create a new virtual environment do

    virtualenv env

Then install OONI with:

   pip install -r requirements.txt

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


