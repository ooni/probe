# -*- mode: ruby -*-
# vi: set ft=ruby :

$setup_ooniprobe = <<SCRIPT
echo "deb http://deb.torproject.org/torproject.org jessie main" >> /etc/apt/sources.list

# Install deb.torproject.org key
gpg --keyserver keys.gnupg.net --recv 886DDD89
gpg --export A3C4F0F979CAA22CDBA8F512EE8CBC9E886DDD89 | apt-key add -

apt-get update

apt-get install -y tor deb.torproject.org-keyring

# Setup for sniffer subsystem
apt-get install -y build-essential libdumbnet-dev libpcap-dev libgeoip-dev libffi-dev python-dev python-pip
cd /data/ooni-probe
python setup.py install

SCRIPT

$setup_oonibackend = <<SCRIPT
echo "Installing Tor..."

echo "deb http://deb.torproject.org/torproject.org jessie main" >> /etc/apt/sources.list

gpg --keyserver keys.gnupg.net --recv 886DDD89
gpg --export A3C4F0F979CAA22CDBA8F512EE8CBC9E886DDD89 | apt-key add -

apt-get update

apt-get -y install deb.torproject.org-keyring tor tor-geoipdb

apt-get -y install curl python-pip python-dev libffi-dev

cd /data/ooni-backend

echo "Generating SSL keys"

openssl genrsa -out private.key 4096
openssl req -new -key private.key -out server.csr -subj '/CN=www.example.com/O=Example/C=AU'

openssl x509 -req -days 365 -in server.csr -signkey private.key -out certificate.crt

cp oonib.conf.example /etc/oonibackend.conf

echo "Installing ooni-backend"
python setup.py install

SCRIPT

Vagrant.configure("2") do |config|
  # Use Debian jessie with the vboxfs contrib add-on
  config.vm.box = "debian/contrib-jessie64"

  config.vm.define "probe" do |probe|
    probe.vm.network "forwarded_port", guest: 8842, host: 8042
    probe.vm.synced_folder ".", "/data/ooni-probe"
    probe.vm.provision :shell, :inline => $setup_ooniprobe
  end

  # If we find a ooni-backend directory in ../ooni-backend we configure a
  # ooni-backend as well.
  if File.directory?("../ooni-backend")
    config.vm.define "backend" do |backend|
      backend.vm.synced_folder "../ooni-backend", "/data/ooni-backend"
      backend.vm.provision :shell, :inline => $setup_oonibackend
    end
  end

  if File.directory?("../ooni-backend")
    config.vm.provision "shell", inline: <<-EOF
      echo "To run oonibackend:"
      echo "1. vagrant ssh backend"
      echo "2. vi /etc/oonibackend.conf  # possibly"
      echo "3. cd /data/ooni-backend"
      echo "4. sudo ./bin/oonib -c /etc/oonibackend.conf"
    EOF
  end

  config.vm.provision "shell", inline: <<-EOF
    echo "To run ooniprobe:"
    echo "1. vagrant ssh probe"
    echo "2. oonideckgen"
    echo "3. ooniprobe -i deck-*/*.deck"
  EOF

end
