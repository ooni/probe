#!/bin/sh
set -e
#
# This script is meant for quick & easy install via:
#   'curl -sSL https://get.ooni.io/ | sh'
# or:
#   'wget -qO- https://get.ooni.io/ | sh'
#
# It is heavily based upon the get.docker.io script

# These are the minimum ubuntu and debian version required to use the debian
# package.
# Currently you can only set the major version number.
MIN_DEBIAN_VERSION=8
MIN_UBUNTU_VERSION=11
TOR_DEB_REPO="http://deb.torproject.org/torproject.org"
INSTALL_PT="yes"

url='https://get.ooni.io/'

command_exists() {
	command -v "$@" > /dev/null 2>&1
}

non_root_usage() {
  your_user=your-user
  [ "$user" != 'root' ] && your_user="$user"
  echo
  echo 'If you would like to run all ooniprobe tests as a non-root user, you should'
  echo 'look at using the ooniprobe non root wrapper:'
  echo
  echo '  https://github.com/TheTorProject/ooni-probe/blob/master/bin/Makefile'
  echo
}

if command_exists ooniprobe; then
	echo >&2 'Warning: "ooniprobe" command appears to already exist.'
	echo >&2 'Please ensure that you do not already have ooniprobe installed.'
	echo >&2 'You may press Ctrl+C now to abort this process and rectify this situation.'
	( set -x; sleep 20 )
fi

user="$(id -un 2>/dev/null || true)"

sh_c='sh -c'
if [ "$user" != 'root' ]; then
	if command_exists sudo; then
		sh_c='sudo sh -c'
	elif command_exists su; then
		sh_c='su -c'
	else
		echo >&2 'Error: this installer needs the ability to run commands as root.'
		echo >&2 'We are unable to find either "sudo" or "su" available to make this happen.'
		exit 1
	fi
fi

curl=''
if command_exists curl; then
	curl='curl --connect-timeout 20 -sSL'
elif command_exists wget; then
	curl='wget --connect-timeout 20 -qO-'
elif command_exists busybox && busybox --list-modules | grep -q wget; then
	curl='busybox wget --connect-timeout 20 -qO-'
fi

if ! (curl $TOR_DEB_REPO | grep "Apache Server at deb.torproject.org");then
  echo '  The Tor Debian repository deb.torproject.org appears to be blocked.'
  echo '  Failing over to using the cloudfronted mirror.'
  TOR_DEB_REPO="https://d3skbh62gb3f3v.cloudfront.net/torproject.org" 
fi

# perform some very rudimentary platform detection
lsb_dist=''
if command_exists lsb_release; then
	lsb_dist="$(lsb_release -si)"
  distro_version="$(lsb_release -rs)"
  distro_codename="$(lsb_release -cs)"
fi
if [ -z "$lsb_dist" ] && [ -r /etc/lsb-release ]; then
	lsb_dist="$(. /etc/lsb-release && echo "$DISTRIB_ID")"
fi
if [ -z "$lsb_dist" ] && [ -r /etc/debian_version ]; then
	lsb_dist='Debian'
  distro_version="$(cat /etc/debian_version)"
  distro_codename="$(. /etc/os-release && echo "$VERSION" | cut -d '(' -f2 | cut -d ')' -f1)"
fi
if [ -z "$lsb_dist" ] && [ -r /etc/fedora-release ]; then
	lsb_dist='Fedora'
fi
if [ -z "$lsb_dist" ] && [ -r /etc/redhat-release ]; then
	lsb_dist='Fedora'
fi

install_obfs4proxy() {

  if ! command_exists go; then
    case "$lsb_dist" in
      Fedora)
        (
          set -x
          $sh_c "yum -y install golang"
        )
        ;;
      Ubuntu|Debian)
        (
          set -x
          $sh_c "apt-get install -y -q golang"
        )
        ;;
    esac
  fi

  if command_exists go; then
    (
      set -x
      export GOPATH=$(mktmp -d)
      go get git.torproject.org/pluggable-transports/obfs4.git/obfs4proxy
      $sh_c "cp $GOPATH/bin/obfs4proxy /usr/local/bin/obfs4proxy"
      $sh_c "chmod +x /usr/local/bin/obfs4proxy"
      rm -rf $GOPATH
    )
  else
    echo >&2
    echo >&2 '  We failed to install go. obfs4proxy will not be installed.'
    echo >&2 '  Please follow the instructions on this page to install it manually:'
    echo >&2
    echo >&2 '    https://github.com/Yawning/obfs4'
    echo >&2
  fi
}

install_pluggable_transports() {
  if [ -z "$INSTALL_PT" ];then
    (
      set -x
      $sh_c 'pip install obfsproxy fteproxy'
    )
    install_obfs4proxy
  fi
}

case "$lsb_dist" in
	Fedora)
		(
			set -x
      $sh_c 'yum -y groupinstall "Development tools"'
      $sh_c 'yum -y install zlib-devel bzip2-devel openssl-devel sqlite-devel libpcap-devel libffi-devel libevent-devel libgeoip-devel tor python-pip'
      $sh_c 'pip install ooniprobe'
		)

    install_pluggable_transports
    non_root_usage
		exit 0
		;;

	Ubuntu|Debian)
		export DEBIAN_FRONTEND=noninteractive

		did_apt_get_update=
		apt_get_update() {
			if [ -z "$did_apt_get_update" ]; then
				( set -x; $sh_c 'sleep 3; apt-get update' )
				did_apt_get_update=1
			fi
		}

    if [ "$TOR_DEBIAN_REPOSITORY" == "https://*" ];then
      (
        set -x
        $sh_c 'apt-get install -y apt-transport-https'
      )
    fi
    
    (
      set -x
		  $sh_c 'apt-key adv --keyserver hkp://pool.sks-keyservers.net --recv-keys A3C4F0F979CAA22CDBA8F512EE8CBC9E886DDD89'
			$sh_c "echo deb $TOR_DEB_REPO $distro_codename main > /etc/apt/sources.list.d/tor.list"
      $sh_c 'apt-get update'
    )

    if [ "$lsb_dist" == 'Debian' ] && 
      [ "$(echo $distro_version | cut -d '.' -f1 )" -gt $MIN_DEBIAN_VERSION ]; then
      (
        set -x
        $sh_c 'apt-get install -y -q ooniprobe'
      )
    elif [ "$lsb_dist" == 'Ubuntu' ] &&
      [ "$(echo $distro_version | cut -d '.' -f1 )" -gt $MIN_UBUNTU_VERSION ]; then
      (
        set -x
        $sh_c 'apt-get install -y -q ooniprobe'
      )
    else
      (
        set -x
        $sh_c 'apt-get install -y -q curl git-core python python-dev python-setuptools build-essential libdumbnet1 python-dumbnet python-libpcap tor tor-geoipdb libgeoip-dev libpcap0.8-dev libssl-dev libffi-dev libdumbnet-dev'
        $sh_c 'pip install ooniprobe'
      )
    fi
    
    install_pluggable_transports
    non_root_usage
		exit 0
		;;

	# Gentoo)
	# 	exit 0
	# 	;;
esac

echo >&2
echo >&2 '  Either your platform is not easily detectable, is not supported by this'
echo >&2 '  installer script (yet - PRs welcome!), or does not yet have a package for'
echo >&2 '  ooniprobe. Please visit the following URL for more detailed installation'
echo >&2 '  instructions:'
echo >&2
echo >&2 '    https://ooni.torproject.org/docs/'
echo >&2
exit 1
