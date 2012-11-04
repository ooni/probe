#!/usr/bin/python

class file:
    def __init__(self, name=None):
        if name:
            self.name = name

    def simple(self, name=None):
        """ Simple file parsing method:
        Read a file line by line and output an array with all it's lines, without newlines
        """
        if name:
            self.name = name
        output = []
        try:
            f = open(self.name, "r")
            for line in f.readlines():
                output.append(line.strip())
            return output
        except:
            return output

    def csv(self, name=None):
        if name:
            self.name = name

    def yaml(self, name):
        if name:
            self.name = name

    def consensus(self, name):
        if name:
            self.name = name
