#!/bin/sh
## You should also create a file from the directory where you run this script
## called torrc with inside the details of the torrc to use.

sudo yum -y groupinstall "Development tools"
sudo yum -y install zlib-devel bzip2-devel openssl-devel ncurses-devel sqlite-devel readline-devel tk-devel gdbm-devel db4-devel libpcap-devel libffi-devel screen libeven-devel unzip
cd `mktemp -d`

# Install Python 2.7.6
wget http://legacy.python.org/ftp//python/2.7.6/Python-2.7.6.tgz
tar xzf Python-2.7.6.tgz
cd Python-2.7.6
./configure --prefix=/usr/local --enable-unicode=ucs4 --enable-shared LDFLAGS="-Wl,-rpath /usr/local/lib"
make
sudo make altinstall
sudo ln -sf /usr/local/bin/python2.7 /usr/bin/python

# Install the latest version of libtool
wget http://ftpmirror.gnu.org/libtool/libtool-2.4.2.tar.gz
tar xzf libtool-2.4.2.tar.gz
cd libtool-2.4.2
./configure
make
sudo make install
sudo mv /usr/bin/libtool /usr/bin/libtool.old
sudo ln -s /usr/local/bin/libtool /usr/bin/libtool

# Install the latest version of autoconf
wget http://ftp.gnu.org/gnu/autoconf/autoconf-2.69.tar.gz
tar xzf autoconf-2.69.tar.gz
cd autoconf-2.69
./configure
make
sudo make install
sudo mv /usr/bin/autoconf /usr/bin/autoconf.old
sudo ln -s /usr/local/bin/autoconf /usr/bin/autoconf

# Install the latest version of automake
wget http://ftp.gnu.org/gnu/automake/automake-1.14.1.tar.gz
tar xzf automake-1.14.1.tar.gz
cd automake-1.14.1
./configure
make
sudo make install
sudo mv /usr/bin/automake /usr/bin/automake.old
sudo ln -s /usr/local/bin/automake /usr/bin/automake

# Install latest version of libevent
wget https://github.com/downloads/libevent/libevent/libevent-2.0.21-stable.tar.gz
tar xvzf libevent-2.0.21-stable.tar.gz
cd libevent-2.0.21-stable
./autogen.sh
./configure
cp /usr/bin/libtool libtool
make
sudo make install

# Install the latest version of Tor
wget -O tor.zip https://github.com/hellais/tor/archive/fix/fedora8.zip
unzip tor.zip
cd tor-fix-fedora8
./autogen.sh
./configure --disable-asciidoc --with-libevent-dir=/usr/local/lib/
make
sudo make install
sudo mv /usr/bin/tor /usr/bin/tor.old
sudo ln -s /usr/local/bin/tor /usr/bin/tor
echo "SocksPort 9050" > /usr/local/etc/tor/torrc
cat torrc >> /usr/local/etc/tor/torrc
/etc/init.d/tor restart

# Install libGeoIP
wget -O master.zip https://github.com/maxmind/geoip-api-c/archive/master.zip
unzip master.zip
cd geoip-api-c-master/
./bootstrap
./configure
make
sudo make install

# Install the latest version of pip
wget https://raw.github.com/pypa/pip/master/contrib/get-pip.py
sudo python get-pip.py

# Install the patched versions of cryptography and pyopenssl
sudo pip install https://github.com/hellais/cryptography/archive/fix/openssl0.9compat.zip
sudo pip install https://github.com/hellais/pyopenssl/archive/fix/openssl0.9.8compat.zip

# Install ooniprobe and obfsproxy
sudo pip install https://github.com/TheTorProject/ooni-probe/archive/master.zip
sudo pip install obfsproxy

# Update the Tor running in ooniprobe
cat ~/.ooni/ooniprobe.conf | sed s/'start_tor: true'/'start_tor: false'/ | sed s/'#socks_port: 8801'/'socks_port: 9050'/ > ~/.ooni/ooniprobe.conf.new
mv ~/.ooni/ooniprobe.conf.new ~/.ooni/ooniprobe.conf

mkdir /home/$USER/bridge_reachability/

# Add cronjob to run ooniprobe daily
{ crontab -l; echo "0 0 * * * $USER ooniprobe -c httpo://e2nl5qgtkzp7cibx.onion blocking/bridge_reachability -f /home/$USER/bridge_reachability/bridges.txt -t 300"; } | crontab
