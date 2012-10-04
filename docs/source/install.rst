
Installing OONI
===============

Currently no installation documentation is present, since OONI is not meant to
be installed and should be handled with care.

Dependencies
************

OONI depends on the following pieces of software.

* Twisted: http://twistedmatrix.com/trac/
* PyYAML: http://pyyaml.org/
* Scapy: http://www.secdev.org/projects/scapy/
    * pypcap: http://code.google.com/p/pypcap/
    * libdnet: http://code.google.com/p/libdnet/

*Optional*

* BeautifulSoup: http://www.crummy.com/software/BeautifulSoup/

Manual installation of scapy
----------------------------

It is optimal to install scapy, libdnet and pypcap from source. This can be
done with the following code snippets.

libdnet::

    wget http://libdnet.googlecode.com/files/libdnet-1.12.tgz
    tar xzf libdnet-1.12.tgz
    cd libdnet-1.12
    ./configure  && make
    cd python/
    sudo python setup.py install
    cd ../../ && rm -rf libdnet-1.12*

pypcap::

    svn checkout http://pypcap.googlecode.com/svn/trunk/ pypcap-read-only
    cd pypcap-read-only/
    sudo pip install pyrex
    make
    sudo python setup.py install
    cd ../ && rm -rf pypcap-read-only

scapy::

    wget http://www.secdev.org/projects/scapy/files/scapy-latest.zip
    unzip scapy-latest.zip
    cd scapy-2.2.0/
    sudo python setup.py install
    cd ../ && rm -rf scapy-*

