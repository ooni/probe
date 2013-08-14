# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  # All Vagrant configuration is done here. The most common configuration
  # options are documented and commented below. For a complete reference,
  # please see the online documentation at vagrantup.com.
  config.vm.box = "precise32"
  config.vm.box_url = "http://files.vagrantup.com/precise32.box"

  config.vm.synced_folder ".", "/usr/share/ooni/"

end

$script = <<SCRIPT
apt-get update
apt-get -y install curl python-setuptools python-dev python-software-properties python-virtualenv virtualenvwrapper vim unzip libpcap-dev

cd /usr/share/ooni/
./setup-dependencies.sh

cd data
make geoip

echo "source ~/.virtualenvs/ooniprobe/bin/activate" >> ~root/.bashrc

mkdir -p ~/.ooni
cp /usr/share/ooni/data/ooniprobe.conf.sample ~/.ooni/ooniprobe.conf

# https://code.google.com/p/pypcap/issues/detail?id=27
# pip install pydnet pypcap

apt-get install tor

echo Login using 'vagrant ssh', and dont forget to run ooniprobe as root.
echo First run: 'sudo su; cd /usr/share/ooni; ./bin/ooniprobe -i decks/before_i_commit.testdeck'

SCRIPT

# TODO: 
# Somehow, ooniprobe is not capable to connect to tor by default. My current 
# workaround is to kill tor, and set "start_tor: true" in /root/.ooni/ooniprobe.conf
#


Vagrant.configure("2") do |config|
    config.vm.provision :shell, :inline => $script
end
