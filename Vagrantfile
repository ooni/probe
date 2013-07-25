# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  # All Vagrant configuration is done here. The most common configuration
  # options are documented and commented below. For a complete reference,
  # please see the online documentation at vagrantup.com.
  config.vm.box = "precise32"
  config.vm.box_url = "http://files.vagrantup.com/precise32.box"

  config.vm.synced_folder ".", "/data/ooniprobe"

end

$script = <<SCRIPT
apt-get update
apt-get -y install curl python-setuptools python-dev python-software-properties python-virtualenv virtualenvwrapper vim

cd /data/ooniprobe
./setup-dependencies.sh

echo "source ~/.virtualenvs/ooniprobe/bin/activate" >> ~root/.bashrc

mkdir -p ~/.ooni
cp /data/ooniprobe/data/ooniprobe.conf.sample ~/.ooni/ooniprobe.conf

echo Login using 'vagrant ssh', and dont forget to run ooniprobe as root.

SCRIPT

Vagrant.configure("2") do |config|
    config.vm.provision :shell, :inline => $script
end
