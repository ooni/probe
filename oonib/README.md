# Dependencies

The extra dependencies necessary to run OONIB are:

* twisted-names
* cyclone: https://github.com/fiorix/cyclone

We recommend that you use a python virtualenv. See OONI's README.md.

# Generate self signed certs for OONIB

If you want to use the HTTPS test helper, you will need to create a certificate:

    openssl genrsa -des3 -out private.key 4096
    openssl req -new -key private.key -out server.csr
    cp private.key private.key.org
    # Remove passphrase from key
    openssl rsa -in private.key.org -out private.key
    openssl x509 -req -days 365 -in server.csr -signkey private.key -out certificate.crt
    rm private.key.org

Don't forget to update oonib/config.py options helpers.ssl.private_key and
helpers.ssl.certificate

# Redirect low ports with iptables

The following iptables commands will map connections on low ports to those bound by oonib

    # Map port 80 to config.helpers.http_return_request.port  (default: 57001)
    iptables -t nat -A PREROUTING -p tcp -m tcp --dport 80 -j REDIRECT --to-ports 57001
    # Map port 443 to config.helpers.ssl.port  (default: 57006)
    iptables -t nat -A PREROUTING -p tcp -m tcp --dport 443 -j REDIRECT --to-ports 57006
    # Map port 53 udp to config.helpers.dns.udp_port (default: 57004)
    iptables -t nat -A PREROUTING -p tcp -m udp --dport 53 -j REDIRECT --tor-ports 
    # Map port 53 tcp to config.helpers.dns.tcp_port (default: 57005)
    iptables -t nat -A PREROUTING -p tcp -m tcp --dport 53 -j REDIRECT --tor-ports 

# Install Tor (Debian).

You will need a Tor binary on your system. For complete instructions, see also:

    https://www.torproject.org/docs/tor-doc-unix.html.en
    https://www.torproject.org/docs/rpms.html.en

Add this line to your /etc/apt/sources.list, replacing <DISTRIBUTION>
where appropriate:

    deb http://deb.torproject.org/torproject.org <DISTRIBUTION> main

Add the Tor Project gpg key to apt:

    gpg --keyserver keys.gnupg.net --recv 886DDD89
    gpg --export A3C4F0F979CAA22CDBA8F512EE8CBC9E886DDD89 | sudo apt-key add -
    # Update apt and install the torproject keyring, tor, and geoipdb
    apt-get update
    apt-get install deb.torproject.org-keyring tor tor-geoipdb

# Update ooni-probe/oonib/config.py

    Set config.main.tor_binary to your Tor path
    Set config.main.tor2webmode = False

# (For Experts Only) Tor2webmode:

WARNING: provides no anonymity! Use only if you know what you are doing!
Tor2webmode will improve the performance of the collector Hidden Service
by discarding server-side anonymity.

You will need to build Tor from source. At the time of writing, the latest stable Tor is tor-0.2.3.25. You should use the most recent stable Tor.

Example:

    git clone https://git.torproject.org/tor.git
    git checkout tor-0.2.3.25
    git verify-tag -v tor-0.2.3.25

You should see:

    object 17c24b3118224d6536c41fa4e1493a831fb29f0a
    type commit
    tag tor-0.2.3.25
    tagger Roger Dingledine <arma@torproject.org> 1353399116 -0500
    
    tag 0.2.3.25
    gpg: Signature made Tue 20 Nov 2012 08:11:59 AM UTC using RSA key ID 19F78451
    gpg: Good signature from "Roger Dingledine <arma@mit.edu>"
    gpg:                 aka "Roger Dingledine <arma@freehaven.net>"
    gpg:                 aka "Roger Dingledine <arma@torproject.org>"

It is always good idea to verify.

    gpg --fingerprint 19F78451
    pub   4096R/19F78451 2010-05-07
          Key fingerprint = F65C E37F 04BA 5B36 0AE6  EE17 C218 5258 19F7 8451
    uid                  Roger Dingledine <arma@mit.edu>
    uid                  Roger Dingledine <arma@freehaven.net>
    uid                  Roger Dingledine <arma@torproject.org>
    sub   4096R/9B11185C 2012-05-02 [expires: 2013-05-02]

Build Tor with enable-tor2web-mode

    ./autogen.sh ; ./configure --enable-tor2web-mode ; make 
    
Copy the tor binary from src/or/tor somewhere and set the corresponding
options in oonib/config.py

# To launch oonib on system boot

To launch oonib on startup, you may want to use supervisord (www.supervisord.org)
The following supervisord config will use the virtual environment in
/home/ooni/venv_oonib and start oonib on boot:

    [program:oonib]
    command=/home/ooni/venv_oonib/bin/python /home/ooni/ooni-probe/bin/oonib
    autostart=true
    user=oonib
    directory=/home/oonib/
