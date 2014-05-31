#!/bin/sh
## You should also create a file from the directory where you run this script
## called torrc with inside the details of the torrc to use.

TMP_INSTALL_DIR=`mktemp -d`

yum_installs() {
  sudo yum -y groupinstall "Development tools" &&
  sudo yum -y install zlib-devel bzip2-devel openssl-devel ncurses-devel sqlite-devel readline-devel tk-devel gdbm-devel db4-devel libpcap-devel libffi-devel screen libeven-devel unzip tor
}

install_python() {
  cd $TMP_INSTALL_DIR;
  # Install Python 2.7.6
  curl -L -o Python-2.7.6.tgz https://www.python.org/ftp/python/2.7.6/Python-2.7.6.tgz &&
  tar xzf Python-2.7.6.tgz &&
  cd Python-2.7.6 &&
  ./configure --prefix=/usr/local --enable-unicode=ucs4 --enable-shared LDFLAGS="-Wl,-rpath /usr/local/lib" &&
  make &&
  sudo make altinstall &&
  sudo ln -sf /usr/local/bin/python2.7 /usr/bin/python
}

install_libtool() {
  # Install the latest version of libtool
  curl -L -o libtool-2.4.2.tar.gz http://ftpmirror.gnu.org/libtool/libtool-2.4.2.tar.gz &&
  tar xzf libtool-2.4.2.tar.gz &&
  cd libtool-2.4.2 &&
  ./configure &&
  make &&
  sudo make install &&
  sudo mv /usr/bin/libtool /usr/bin/libtool.old &&
  sudo ln -s /usr/local/bin/libtool /usr/bin/libtool
}

install_autoconf() {
  # Install the latest version of autoconf
  curl -L -o autoconf-2.69.tar.gz http://ftp.gnu.org/gnu/autoconf/autoconf-2.69.tar.gz &&
  tar xzf autoconf-2.69.tar.gz &&
  cd autoconf-2.69 &&
  ./configure &&
  make && 
  sudo make install &&
  sudo mv /usr/bin/autoconf /usr/bin/autoconf.old &&
  sudo ln -s /usr/local/bin/autoconf /usr/bin/autoconf
}

install_automake(){
  # Install the latest version of automake
  curl -L -o automake-1.14.1.tar.gz http://ftp.gnu.org/gnu/automake/automake-1.14.1.tar.gz &&
  tar xzf automake-1.14.1.tar.gz &&
  cd automake-1.14.1 &&
  ./configure &&
  make &&
  sudo make install &&
  sudo mv /usr/bin/automake /usr/bin/automake.old &&
  sudo ln -s /usr/local/bin/automake /usr/bin/automake
}

install_libevent(){
  # Install latest version of libevent
  curl -L -o libevent-2.0.21-stable.tar.gz https://github.com/downloads/libevent/libevent/libevent-2.0.21-stable.tar.gz &&
  tar xvzf libevent-2.0.21-stable.tar.gz &&
  cd libevent-2.0.21-stable &&
  ./autogen.sh &&
  ./configure &&
  cp /usr/bin/libtool libtool &&
  make &&
  sudo make install
}

install_gmp() {
  # Install GMP
  curl -L -o gmp-6.0.0a.tar.bz2 https://gmplib.org/download/gmp/gmp-6.0.0a.tar.bz2 &&
  tar xjpf gmp-6.0.0a.tar.bz2 &&
  cd gmp-6.0.0 &&
  export ABI=32 &&
  ./configure --enable-cxx &&
  make &&
  sudo make install
}

install_tor() {
  # Install the latest version of Tor
  curl -L -o tor.zip https://github.com/hellais/tor/archive/fix/fedora8.zip &&
  unzip tor.zip &&
  cd tor-fix-fedora8 &&
  ./autogen.sh &&
  ./configure --disable-asciidoc --with-libevent-dir=/usr/local/lib/ &&
  make &&
  sudo make install &&
  sudo mv /usr/bin/tor /usr/bin/tor.old &&
  sudo ln -s /usr/local/bin/tor /usr/bin/tor &&
  echo "SocksPort 9050" > torrc &&
  sudo mv torrc /usr/local/etc/tor/torrc &&
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
  sudo mv tor.init /etc/init.d/tor &&
  sudo chmod +x /etc/init.d/tor &&
  sudo /etc/init.d/tor restart

}

install_geoip() {
  # Install libGeoIP
  curl -L -o master.zip https://github.com/maxmind/geoip-api-c/archive/master.zip &&
  unzip master.zip &&
  cd geoip-api-c-master/ &&
  ./bootstrap &&
  ./configure &&
  make &&
  sudo make install
}

install_pip() {
  # Install the latest version of pip
  curl -L -o get-pip.py https://raw.githubusercontent.com/pypa/pip/master/contrib/get-pip.py &&
  sudo python get-pip.py
}

install_cryptography() {
  # Install the patched versions of cryptography, pyopenssl and pycrypto
  # This is needed to avoid this bug: https://groups.google.com/forum/#!topic/ikarus-users/_R0QHqwyYz8
  export ac_cv_func_malloc_0_nonnull=yes
  sudo -E `which pip` install PyCrypto &&
  sudo `which pip` install cryptography &&
  sudo `which pip` install https://github.com/pyca/pyopenssl/archive/master.zip
}

install_pluggable_transports() {
  # Install pluggable transport related stuff
  sudo `which pip` install obfsproxy
  curl -L -o 0.2.9.zip https://github.com/kpdyer/fteproxy/archive/0.2.9.zip
  unzip 0.2.9.zip
  cd fteproxy-0.2.9
  make
  sudo cp bin/fteproxy /usr/bin/fteproxy
  sudo python setup.py install
}

install_ooniprobe() {
  # Install ooniprobe and obfsproxy
  sudo `which pip` install https://github.com/TheTorProject/ooni-probe/archive/master.zip &&
  /usr/local/bin/ooniprobe --version
}

setup_ooniprobe() {
  # Update the Tor running in ooniprobe
  mkdir ~/.ooni/
  cat /usr/share/ooni/ooniprobe.conf.sample | sed s/'start_tor: true'/'start_tor: false'/ | sed s/'#socks_port: 8801'/'socks_port: 9050'/ > ~/.ooni/ooniprobe.conf &&

  mkdir /home/$USER/bridge_reachability/ &&

  # Add cronjob to run ooniprobe daily
  { crontab -l; echo "PATH=\$PATH:/usr/local/bin/\n0 0 * * * /usr/local/bin/ooniprobe -c httpo://e2nl5qgtkzp7cibx.onion blocking/bridge_reachability -f /home/$USER/bridge_reachability/bridges.txt -t 300"; } | crontab &&
  sudo /etc/init.d/crond start &&
  sudo /sbin/chkconfig crond on &&
  sudo chmod 777 /var/mail
}

run_or_exit() {
  command=$1
  cd $TMP_INSTALL_DIR &&
  echo "[*] Running" $command
  $command
  return_value=$?
  if [ $return_value -ne 0 ]; then
    echo "[!] Failed to run" $command
    exit 1
  fi
  echo "[*] Completed running" $command
}

run_or_exit yum_installs
run_or_exit install_python
run_or_exit install_libtool
run_or_exit install_autoconf
run_or_exit install_automake
run_or_exit install_libevent
run_or_exit install_gmp
run_or_exit install_tor
run_or_exit install_geoip
run_or_exit install_pip
run_or_exit install_cryptography
run_or_exit install_pluggable_transports
run_or_exit install_ooniprobe
run_or_exit setup_ooniprobe
