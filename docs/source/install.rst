
Installing OONI
===============

Currently no installation documentation is present, since OONI is not meant to
be installed and should be handled with care.

Dependencies
************

OONI depends on the following pieces of software.

* Twisted (>12.0.0): http://twistedmatrix.com/trac/
* PyYAML: http://pyyaml.org/
* Scapy: http://www.secdev.org/projects/scapy/
    * pypcap: http://code.google.com/p/pypcap/
    * libdnet: http://code.google.com/p/libdnet/
* BeautifulSoup: http://www.crummy.com/software/BeautifulSoup/

*Optional*

* Dnspython[1]: http://www.dnspython.org/
* Paramiko[2]: http://www.lag.net/paramiko/
* Txtorcon: https://github.com/meejah/txtorcon

[1][2] These dependencies will soon be removed completely.

Debian packages
---------------

On debian you can install most of the dependecies with apt-get with this command::

    apt-get install python-yaml python-scapy python-beautifulsoup python-pypcap python-dumbnet python-dnspython

Note that debian (squeeze) distributes version 10.1.0 of python-twisted,
and ubuntu (precise) distributes version 11.1.0.
You need the following packages for twisted to compile::

    apt-get install python-dev build-essential

Txtorcon has the following addtitional dependencies::
    
    apt-get install python-geoip python-ipaddr python-psutil  

Python virtual environmentsa (virtualenv)
-----------------------------------------

You may prefer to install these dependencies within a python virtualenv[3]::

    sudo apt-get install python-virtualenv virtualenvwrapper

From the docs (/usr/share/doc/virtualenvwrapper/README.Debian):

    Virtualenvwrapper is enabled if you install the package bash-completion and
    enable bash completion support in /etc/bash.bashrc or your ~/.bashrc.

    If you only want to use virtualenvwrapper you may just add
    source /etc/bash_completion.d/virtualenvwrapper to your ~/.bashrc.

Source the script or login again and set up a virtualenv::

    mkdir $HOME/.virtualenvs
    mkvirtualenv ooni-probe

You will automatically enter the environment. easy_install and pip will install
packages inside this environment, and will not require root privileges.
[3] http://www.virtualenv.org

Manual installation of  python dependencies
-------------------------------------------

This involves installing the dependencies installable via easy_install/pip and
the ones that are not by building them from source.

"simple" dependencies via easy_install::

    sudo easy_install pyyaml
    sudo easy_install twisted
    sudo easy_install beautifulsoup
    sudo easy_install pygeoip
    sudo easy_install six
    sudo easy_install ipaddr
    sudo easy_install psutil
    sudo easy_install txtorcon

"simple" dependencies via pip::

    sudo pip install pyyaml
    sudo pip install twisted
    sudo pip install beautifulsoup
    sudo pip install pygeoip
    sudo pip install six
    sudo pip install ipaddr
    sudo pip install psutil
    sudo pip install txtorcon

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
