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
cd /ooni/
export USE_VIRTUALENV=0
./setup-dependencies.sh -y
python setup.py install

cd /usr/share/ooni/
echo "[+] Building geoip stuff.."
make geoip 2>&1 > /dev/null

mkdir -p ~/.ooni
cp /usr/share/ooni/ooniprobe.conf.sample ~/.ooni/ooniprobe.conf

cd /ooni/inputs/
make lists 2>&1 > /dev/null

# https://code.google.com/p/pypcap/issues/detail?id=27
# pip install pydnet pypcap

echo Login using 'vagrant ssh', and dont forget to run ooniprobe as root.
echo First run: 'sudo su; cd /usr/share/ooni; ./bin/ooniprobe -i decks/before_i_commit.testdeck'

SCRIPT

# TODO: 
# Somehow, ooniprobe is not capable to connect to tor by default. My current 
# workaround is to kill tor, and set "start_tor: true" in /root/.ooni/ooniprobe.conf

Vagrant.configure("2") do |config|
    config.vm.provision :shell, :inline => $script
end
