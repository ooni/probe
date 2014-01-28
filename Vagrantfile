# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  # All Vagrant configuration is done here. The most common configuration
  # options are documented and commented below. For a complete reference,
  # please see the online documentation at vagrantup.com.
  config.vm.box = "precise32"
  config.vm.box_url = "http://files.vagrantup.com/precise32.box"

  config.vm.synced_folder ".", "/ooni"

end

$script = <<SCRIPT

echo "deb http://deb.ooni.nu/ooni wheezy main" >> /etc/apt/sources.list
echo "deb http://deb.torproject.org/torproject.org precise main" >> /etc/apt/sources.list

# Install deb.ooni.nu key
gpg --keyserver pgp.mit.edu --recv-key 0x49B8CDF4
gpg --export 89AB86D4788F3785FE9EDA31F9E2D9B049B8CDF4 | apt-key add -

# Install deb.torproject.org key
gpg --keyserver keys.gnupg.net --recv 886DDD89
gpg --export A3C4F0F979CAA22CDBA8F512EE8CBC9E886DDD89 | apt-key add -

apt-get update

apt-get install -y tor deb.torproject.org-keyring
apt-get install -y ooniprobe

echo "Login using 'vagrant ssh', and dont forget to run ooniprobe as root."
echo "First run: 'sudo ooniprobe -i /usr/share/ooni/decks/fast.deck'"

SCRIPT

# TODO: 
# Somehow, ooniprobe is not capable to connect to tor by default. My current 
# workaround is to kill tor, and set "start_tor: true" in /root/.ooni/ooniprobe.conf

Vagrant.configure("2") do |config|
    config.vm.provision :shell, :inline => $script
end
