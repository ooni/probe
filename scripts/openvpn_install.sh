#!/bin/sh

set -e

user="$(id -un 2>/dev/null || true)"

sh_c='sh -c'

if [ "$user" != 'root' ]; then
	if command_exists sudo; then
		sh_c='sudo sh -c -E'
	elif command_exists su; then
		sh_c='su -c --preserve-environment'
	else
		echo >&2 'Error: this installer needs the ability to run commands as root.'
		echo >&2 'We are unable to find either "sudo" or "su" available to make this happen.'
		exit 1
	fi
fi

$sh_c "apt-get -y install openvpn"
