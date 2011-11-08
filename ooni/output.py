import yaml

class yaml:
    def __init__(self, name=None):
        if name:
            self.name = name

    def output(self, data, name=None):
        if name:
            self.name = name
        try:
            stream = open(name, 'w')
            yaml.dump(data, stream)
            stream.close()
        except:
            pass


