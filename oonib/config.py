from ooni.utils import Storage
import os

def get_root_path():
    this_directory = os.path.dirname(__file__)
    root = os.path.join(this_directory, '..')
    root = os.path.abspath(root)
    return root

backend_version = '0.0.1'

# XXX convert this to something that is a proper config file
main = Storage()

# This is the location where submitted reports get stored
main.report_dir = os.path.join(get_root_path(), 'oonib', 'reports')

# This is where tor will place it's Hidden Service hostname and Hidden service
# private key
main.tor_datadir = os.path.join(get_root_path(), 'oonib', 'data', 'tor')

main.database_uri = "sqlite:"+get_root_path()+"oonib_test_db.db"
main.db_threadpool_size = 10
#main.tor_binary = '/usr/sbin/tor'
main.tor_binary = '/usr/local/bin/tor'

helpers = Storage()

helpers.http_return_request = Storage()
helpers.http_return_request.port = 57001
# XXX this actually needs to be the advertised Server HTTP header of our web
# server
helpers.http_return_request.server_version = "Apache"

helpers.tcp_echo = Storage()
helpers.tcp_echo.port = 57002

helpers.daphn3 = Storage()
#helpers.daphn3.yaml_file = "/path/to/data/oonib/daphn3.yaml"
#helpers.daphn3.pcap_file = "/path/to/data/server.pcap"
helpers.daphn3.port = 57003

helpers.dns = Storage()
helpers.dns.udp_port = 57004
helpers.dns.tcp_port = 57005

helpers.ssl = Storage()
#helpers.ssl.private_key = /path/to/data/private.key
#helpers.ssl.certificate = /path/to/data/certificate.crt
#helpers.ssl.port = 57006


