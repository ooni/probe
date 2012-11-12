from ooni.utils import Storage
import os

def get_root_path():
    this_directory = os.path.dirname(__file__)
    root = os.path.join(this_directory, '..')
    root = os.path.abspath(root)
    return root

# XXX convert this to something that is a proper config file
main = Storage()
main.collector_port = 8888

# XXX make this be the server name that is of 
main.database_uri = "sqlite:"+get_root_path()+"oonib_test_db.db"
main.db_threadpool_size = 10

helpers = Storage()

helpers.http_return_request = Storage()
helpers.http_return_request.port = 57001
# XXX this actually needs to be the advertised Server HTTP header of our web
# server
helpers.http_return_request.server_version = "Apache"

helpers.tcp_echo = Storage()
helpers.tcp_echo.port = 57002

helpers.daphn3 = Storage()
helpers.daphn3.yaml_file = "/path/to/data/oonib/daphn3.yaml"
helpers.daphn3.pcap_file = "/path/to/data/server.pcap"
helpers.daphn3.port = 57003

helpers.dns = Storage()
helpers.dns.udp_port = 57004
helpers.dns.tcp_port = 57005

helpers.ssl = Storage()
#helpers.ssl.private_key = /path/to/data/private.key
#helpers.ssl.certificate = /path/to/data/certificate.crt
#helpers.ssl.port = 57007


