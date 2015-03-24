# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  # All Vagrant configuration is done here. The most common configuration
  # options are documented and commented below. For a complete reference,
  # please see the online documentation at vagrantup.com.
  config.vm.box = "precise32"
  config.vm.box_url = "http://files.vagrantup.com/precise32.box"

  config.vm.synced_folder ".", "/ooni"
  # Place the ooni-backend source code in ../ooni-backend to sync it with the vagrant instance
  config.vm.synced_folder "../ooni-backend", "/backend"

  config.vm.network :private_network, ip: "192.168.38.20"

end

$script = <<SCRIPT

echo "deb http://deb.torproject.org/torproject.org precise main" >> /etc/apt/sources.list

# Install deb.torproject.org key
gpg --keyserver keys.gnupg.net --recv 886DDD89
gpg --export A3C4F0F979CAA22CDBA8F512EE8CBC9E886DDD89 | apt-key add -

apt-get update

apt-get install -y tor deb.torproject.org-keyring

# Setup for sniffer subsystem
apt-get install -y build-essential libdumbnet-dev python-dumbnet python-pypcap libpcap-dev python-dev python-pip libgeoip-dev libffi-dev
cd /ooni
python setup.py install
echo "Login using 'vagrant ssh', and dont forget to run ooniprobe as root."
echo "First run: 'sudo ooniprobe -i /usr/share/ooni/decks/fast.deck'"

SCRIPT

# TODO: 
# Somehow, ooniprobe is not capable to connect to tor by default. My current 
# workaround is to kill tor, and set "start_tor: true" in /root/.ooni/ooniprobe.conf

Vagrant.configure("2") do |config|
    config.vm.provision :shell, :inline => $script
end
