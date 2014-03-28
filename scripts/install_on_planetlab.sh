#!/bin/sh
## You should also create a file from the directory where you run this script
## called torrc with inside the details of the torrc to use.

sudo yum -y groupinstall "Development tools"
sudo yum -y install zlib-devel bzip2-devel openssl-devel ncurses-devel sqlite-devel readline-devel tk-devel gdbm-devel db4-devel libpcap-devel libffi-devel screen libeven-devel unzip tor
cd `mktemp -d`

# Install Python 2.7.6
curl -o Python-2.7.6.tgz http://legacy.python.org/ftp//python/2.7.6/Python-2.7.6.tgz
tar xzf Python-2.7.6.tgz
cd Python-2.7.6
./configure --prefix=/usr/local --enable-unicode=ucs4 --enable-shared LDFLAGS="-Wl,-rpath /usr/local/lib"
make
sudo make altinstall
sudo ln -sf /usr/local/bin/python2.7 /usr/bin/python
cd ..

# Install the latest version of libtool
curl -o libtool-2.4.2.tar.gz http://ftpmirror.gnu.org/libtool/libtool-2.4.2.tar.gz
tar xzf libtool-2.4.2.tar.gz
cd libtool-2.4.2
./configure
make
sudo make install
sudo mv /usr/bin/libtool /usr/bin/libtool.old
sudo ln -s /usr/local/bin/libtool /usr/bin/libtool
cd ..

# Install the latest version of autoconf
curl -o autoconf-2.69.tar.gz http://ftp.gnu.org/gnu/autoconf/autoconf-2.69.tar.gz
tar xzf autoconf-2.69.tar.gz
cd autoconf-2.69
./configure
make
sudo make install
sudo mv /usr/bin/autoconf /usr/bin/autoconf.old
sudo ln -s /usr/local/bin/autoconf /usr/bin/autoconf
cd ..

# Install the latest version of automake
curl -o automake-1.14.1.tar.gz http://ftp.gnu.org/gnu/automake/automake-1.14.1.tar.gz
tar xzf automake-1.14.1.tar.gz
cd automake-1.14.1
./configure
make
sudo make install
sudo mv /usr/bin/automake /usr/bin/automake.old
sudo ln -s /usr/local/bin/automake /usr/bin/automake
cd ..

# Install latest version of libevent
curl -o libevent-2.0.21-stable.tar.gz https://github.com/downloads/libevent/libevent/libevent-2.0.21-stable.tar.gz
tar xvzf libevent-2.0.21-stable.tar.gz
cd libevent-2.0.21-stable
./autogen.sh
./configure
cp /usr/bin/libtool libtool
make
sudo make install
cd ..

# Install GMP
curl -o gmp-6.0.0a.tar.bz2 https://gmplib.org/download/gmp/gmp-6.0.0a.tar.bz2
tar xjpf gmp-6.0.0a.tar.bz2
cd gmp-6.0.0
export ABI=32
./configure --enable-cxx
make
sudo make install
cd ..

# Install the latest version of Tor
curl -o tor.zip https://github.com/hellais/tor/archive/fix/fedora8.zip
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
cat <<EOF > tor.init
RETVAL=0
prog="tor"

# Source function library.
. /etc/init.d/functions


start() {
  echo -n $"Starting \$prog: "
  daemon \$prog --runasdaemon 1 && success || failure
  RETVAL=\$?
  echo
  return \$RETVAL
}

stop() {
  echo -n $"Stopping \$prog: "
        killall \$prog
  RETVAL=\$?
  echo
  return \$RETVAL
}

case "\$1" in
  start)
    start
  ;;
  stop)
    stop
  ;;
  restart)
  stop
    start
  ;;
  *)
  echo $"Usage: \$0 {start|stop|restart}"
  RETVAL=3
esac
exit \$RETVAL
EOF
sudo mv tor.init /etc/init.d/tor
sudo chmod +x /etc/init.d/tor
sudo /etc/init.d/tor restart
cd ..

# Install libGeoIP
curl -o master.zip https://github.com/maxmind/geoip-api-c/archive/master.zip
unzip master.zip
cd geoip-api-c-master/
./bootstrap
./configure
make
sudo make install
cd ..

# Install the latest version of pip
curl -o get-pip.py https://raw.github.com/pypa/pip/master/contrib/get-pip.py
sudo python get-pip.py

# Install the patched versions of cryptography and pyopenssl
sudo pip install cryptography
sudo pip install https://github.com/pyca/pyopenssl/archive/master.zip

# Install pluggable transport related stuff
sudo pip install obfsproxy
curl -o 0.2.9.zip https://github.com/kpdyer/fteproxy/archive/0.2.9.zip
unzip 0.2.9.zip
cd fteproxy-0.2.9
make
sudo cp bin/fteproxy /usr/bin/fteproxy
sudo python setup.py install
cd ..

# Install ooniprobe and obfsproxy
sudo pip install https://github.com/TheTorProject/ooni-probe/archive/master.zip
/usr/local/bin/ooniprobe

# Update the Tor running in ooniprobe
cat /usr/share/ooni/ooniprobe.conf.sample | sed s/'start_tor: true'/'start_tor: false'/ | sed s/'#socks_port: 8801'/'socks_port: 9050'/ > ~/.ooni/ooniprobe.conf

mkdir /home/$USER/bridge_reachability/

# Add cronjob to run ooniprobe daily
{ crontab -l; echo "PATH=\$PATH:/usr/local/bin/\n0 0 * * * /usr/local/bin/ooniprobe -c httpo://e2nl5qgtkzp7cibx.onion blocking/bridge_reachability -f /home/$USER/bridge_reachability/bridges.txt -t 300"; } | crontab
sudo /etc/init.d/crond start
sudo /sbin/chkconfig crond on
sudo chmod 777 /var/mail
