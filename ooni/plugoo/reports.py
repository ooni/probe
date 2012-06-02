import os
import yaml

import itertools
from ooni import log, date

class Report:
    """This is the ooni-probe reporting mechanism. It allows
    reporting to multiple destinations and file formats.

    :scp the string of <host>:<port> of an ssh server

    :yaml the filename of a the yaml file to write

    :file the filename of a simple txt file to write

    :tcp the <host>:<port> of a TCP server that will just listen for
         inbound connection and accept a stream of data (think of it
         as a `nc -l -p <port> > filename.txt`)
    """
    def __init__(self, testname=None, file="report.log",
                 scp=None,
                 tcp=None):

        self.testname = testname
        self.file = file
        self.tcp = tcp
        self.scp = scp
        #self.config = ooni.config.report

        #if self.config.timestamp:
        #    tmp = self.file.split('.')
        #    self.file = '.'.join(tmp[:-1]) + "-" + \
        #                datetime.now().isoformat('-') + '.' + \
        #                tmp[-1]
        #    print self.file

        self.scp = None
        self.write_header()

    def write_header(self):
        pretty_date = date.pretty_date()
        header = "# OONI Probe Report for Test %s\n" % self.testname
        header += "# %s\n\n" % pretty_date
        self._write_to_report(header)
        # XXX replace this with something proper
        test_details = {'start_time': date.now(),
                        'asn': 'ASN-1234',
                        'test_name': self.testname,
                        'addr': '1234'}
        self(test_details)

    def _write_to_report(self, dump):
        reports = []

        if self.file:
            reports.append("file")

        if self.tcp:
            reports.append("tcp")

        if self.scp:
            reports.append("scp")

        #XXX make this non blocking
        for report in reports:
            self.send_report(dump, report)

    def __call__(self, data):
        """
        This should be invoked every time you wish to write some
        data to the reporting system
        """
        #print "Writing report(s)"
        #dump = '--- \n'
        dump = yaml.dump([data])
        #dump += yaml.dump(data)

        self._write_to_report(dump)

    def file_report(self, data, file=None, mode='a+'):
        """
        This reports to a file in YAML format
        """
        if not file:
            file = self.file
        try:
            f = open(file, mode)
            f.write(data)
        except Exception, e:
            raise e
        finally:
            f.close()


    def tcp_report(self, data):
        """
        This connect to the specified tcp server
        and writes the data passed as argument.
        """
        host, port = self.tcp.split(":")
        tcp = socket.getprotobyname('tcp')
        send_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, tcp)
        try:
            send_socket.connect((host, int(port)))
            send_socket.send(data)

        except Exception, e:
            raise e

        finally:
            send_socket.close()


    def scp_report(self, data, rfile=None, mode='a+'):
        """
        Push data to the remote ssh server.

        :rfile the remote filename to write
        :data the raw data content that should be written
        :mode in what mode the file should be created
        """
        if not rfile:
            rfile = self.file
        host, port = self.scp.split(":")
        transport = paramiko.Transport((host, port))

        # The remote path of the remote file to write
        rfpath = os.path.join(self.config.ssh_rpath, rfile)

        try:
            username = self.config.ssh_username
        except:
            raise "No username provided"

        # Load the local known host key file
        transport.load_host_keys(os.path.expanduser("~/.ssh/known_hosts"))

        # We prefer to use an ssh keyfile fo authentication
        if self.config.ssh_keyfile:
            keyfile = os.path.expanduser(self.config.ssh_keyfile)
            key = paramiko.RSAKey.from_private_key_file(keylocfile)
            try:
                transport.connect(username=username, pkey=key)
            except Exception, e:
                raise e

        # If not even a password is fine
        elif self.config.ssh_password:
            try:
                transport.connect(username=username, password=self.config.ssh_password)
            except Exception, e:
                raise e

        # ... but no authentication, that is madness!
        else:
            raise "No key or password provided for ssh"

        sftp = paramiko.SFTPClient.from_transport(transport)
        try:
            sftp = ssh.open_sftp()
            remote_file = sftp.file(rfile, mode)
            remote_file.set_pipelined(True)
            remote_file.write(data)

        except Exception, e:
            raise e
        sftp.close()
        transport.close()


    def send_report(self, data, type):
        """
        This sends the report using the
        specified type.
        """
        #print "Reporting %s to %s" % (data, type)
        log.msg("Reporting to %s" % type)
        getattr(self, type+"_report").__call__(data)


