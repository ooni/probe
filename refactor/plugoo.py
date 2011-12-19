# This contains all of the "goo" necessary for creating
# ooni-probe plugoonies.

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
        if self.fh:
            line = self.fh.readline()
            if line:
                return line.replace('\n','')
            else:
                self.fh.seek(0)
                raise StopIteration
        else:
            raise StopIteration
    
    def next(self):
        try:
            return self.next_asset()
        except:
            raise StopIteration


class Plugoo():
    def __init__(self, config):
        self.config = config
    
    def experiment(self, *a, **b):
        pass
    
    def control(self, *a, **b):
        pass
    
    def compare(self, *a, **b):
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
        jobs = []
        if assets:
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
         
    
