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

    
    def scp(self, rfile, data):
        host, port = self.scp.split(":")
        transport = paramiko.Transport((host, port))
        
        try:
            username = self.config.ssh_username
        except:
            raise "No username provided"
        
        transport.load_host_keys(os.path.expanduser("~/.ssh/known_hosts"))
        
        if self.config.ssh_keyfile:
            keyfile = os.path.expanduser(self.config.ssh_keyfile)
            key = paramiko.RSAKey.from_private_key_file(keylocfile)
            try:
                transport.connect(username=username, pkey=key)
            except Exception, e:
                raise e
            
        elif self.config.ssh_password:
            try:
                transport.connect(username=username, password=self.config.ssh_password)
            except Exception, e:
                raise e
        else:
            raise "No key or password provided for ssh"

        sftp = paramiko.SFTPClient.from_transport(transport)
        try:
            sftp = ssh.open_sftp()
            remote_file = sftp.file(rfile, "wb")
            remote_file.set_pipelined(True)
            remote_file.write(data)
            
        except Exception, e:
            raise e
        sftp.close()
        transport.close()
    

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
         
    
