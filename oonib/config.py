from ooni.utils import Storage
import os

# XXX convert this to something that is a proper config file
main = Storage()
main.reporting_port = 8888
main.http_port = 8080
main.dns_udp_port = 5354
main.dns_tcp_port = 8002
main.daphn3_port = 9666
main.server_version = "Apache"
#main.ssl_private_key = /path/to/data/private.key
#main.ssl_certificate = /path/to/data/certificate.crt
#main.ssl_port = 8433

helpers = Storage()
helpers.http_return_request_port = 1234

daphn3 = Storage()
daphn3.yaml_file = "/path/to/data/oonib/daphn3.yaml"
daphn3.pcap_file = "/path/to/data/server.pcap"
