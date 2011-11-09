import yaml

class data:
    def __init__(self, name=None):
        if name:
            self.name = name

    def output(self, data, name=None):
        if name:
            self.name = name

        stream = open(self.name, 'w')
        yaml.dump(data, stream)
        stream.close()
    def append(self, data, name=None):
        if name:
            self.name = name
        stream = open(self.name, 'a')
        yaml.dump([data], stream)
        stream.close()

