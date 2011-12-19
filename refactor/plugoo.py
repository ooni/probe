# This contains all of the "goo" necessary for creating
# ooni-probe plugoonies.

import os

import logging
import itertools
import gevent

class Asset:
    """This is an ooni-probe asset. It is a python
    iterator object, allowing it to be efficiently looped.
    To create your own custom asset your should subclass this
    and override the next_asset method and the len method for
    computing the length of the asset.
    """
    def __init__(self, file=None):
        self.fh = None
        if file:
            self.name = file
            self.fh = open(file, 'r')
        self.eof = False
    
    def __iter__(self):
        return self

    def len(self):
        """Returns the length of the asset
        """
        for i, l in enumerate(self.fh):
            pass
        # rewind the file
        self.fh.seek(0)
        return i + 1
        
    def next_asset(self):
        """Return the next asset.
        """
        # XXX this is really written with my feet.
        #     clean me up please...
        line = self.fh.readline()
        if line:
            return line.replace('\n','')
        else:
            self.fh.seek(0)
            raise StopIteration
    
    def next(self):
        try:
            return self.next_asset()
        except:
            raise StopIteration


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
    def __init__(self, ooni, 
                 scp="127.0.0.1:22", 
                 yaml="test.yaml", 
                 file="test.report",
                 tcp="127.0.0.1:9000"):
        
        self.file = file
        self.yaml = yaml
        self.tcp = tcp
        self.scp = scp
        self.config = ooni.config.report
        
        try:
            import paramiko
        except:
            self.scp = None
            ooni.logger("Could not import paramiko. SCP will not be disabled")

    
    def scp(self, rfile, data, mode='wb'):
        """Push data to the remote ssh server.
        :rfile the remote filename to write
        :data the raw data content that should be written
        :mode in what mode the file should be created
        """
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

    def report(self):
        """This should be invoked every time you wish to write some re
        """

class Plugoo():
    def __init__(self, ooni):
        self.config = ooni.config
        self.logger = ooni.logger
        self.name = "test"
    
    def experiment(self, *a, **b):
        pass
    
    def control(self, *a, **b):
        pass
    
    def compare(self, *a, **b):
        """Override this method to write your own
        Plugoo.
        """
        pass
    
    def load_assets(self, assets):
        """Takes as input an array of Asset objects and
        outputs an iterator for the loaded assets.
        example:
        assets = [hostlist, portlist, requestlist]
        
        """
        bigsize = 0
        bigidx = 0
        for i, v in enumerate(assets):
            size = v.len()
            if size > bigsize:
                bigidx, bigsize = (i, size)
        
        smallassets = list(assets)
        smallassets.pop(bigidx)                
            
        for x in assets[bigidx]:
            # XXX this will only work in python 2.6, maybe refactor
            for comb in itertools.product(*smallassets):
                yield (x,) + comb
            
               
    def run(self, assets=None, buffer=100, timeout=2):
        logger.info("Starting %s", self.name)
        jobs = []
        if assets:
            logger.debug("Runnig through tests")
            for i, data in enumerate(self.load_assets(assets)):
                args = {'data': data}
                # Append to the job queue
                jobs.append(gevent.spawn(self.compare, **args))
                # If the buffer is full run the jobs
                if i % buffer == 0:
                    # Run the jobs with the selected timeout
                    gevent.joinall(jobs, timeout=timeout)
                    for job in jobs:
                        print job.value
                    jobs = []
