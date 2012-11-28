# Dependencies

The extra dependencies necessary to run OONIB are:

* twisted-names
* cyclone: https://github.com/fiorix/cyclone

# Generate self signed certs for OONIB

    openssl genrsa -des3 -out private.key 4096
    openssl req -new -key private.key -out server.csr
    cp private.key private.key.org
    # Remove passphrase from key
    openssl rsa -in private.key.org -out private.key
    openssl x509 -req -days 365 -in server.csr -signkey private.key -out certificate.crt
    rm private.key.org

# Redirect low ports with iptables

    # Map port 80 to config.helpers.http_return_request.port  (default: 57001)
    iptables -t nat -A PREROUTING -p tcp -m tcp --dport 80 -j REDIRECT --to-ports 57001
    # Map port 443 to config.helpers.ssl.port  (default: 57006)
    iptables -t nat -A PREROUTING -p tcp -m tcp --dport 443 -j REDIRECT --to-ports 57006
