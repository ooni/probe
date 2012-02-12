"""

"""

import imp
import logging

class Storage(dict):
    """
    A Storage object is like a dictionary except `obj.foo` can be used
    in addition to `obj['foo']`.

        >>> o = Storage(a=1)
        >>> o.a
        1
        >>> o['a']
        1
        >>> o.a = 2
        >>> o['a']
        2
        >>> del o.a
        >>> o.a
        None
    """

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError, k:
            return None

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError, k:
            raise AttributeError, k

    def __repr__(self):
        return '<Storage ' + dict.__repr__(self) + '>'

    def __getstate__(self):
        return dict(self)

    def __setstate__(self, value):
        for (k, v) in value.items():
            self[k] = v


def get_logger(config):
    loglevel = getattr(logging, config.loglevel.upper())
    logging.basicConfig(level=loglevel,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    filename=config.logfile,
                    filemode='w')

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    # Set the console logger to a different format
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

    return logging.getLogger('ooni-probe')

def parse_asset(asset):
    parsed = Storage()
    try:
        with open(asset, 'r') as f:
            for line in f.readlines():
            # XXX This should be rewritten, if the values contain
            #     #: they will be rewritten with blank.
            # should not be an issue but this is not a very good parser
                if line.startswith("#:"):
                    n = line.split(' ')[0].replace('#:','')
                    v = line.replace('#:'+n+' ', '').strip()
                    if n in ('tests', 'files'):
                        parsed[n] = v.split(",")
                    else:
                        parsed[n] = v
                        
                elif line.startswith("#"):
                    continue
                else:
                        break
    finally:
        if not parsed.name:
            parsed.name = asset
        if not parsed.files:
            parsed.files = asset
        return parsed

def import_test(name, config):
    if name.endswith(".py"):
        test = Storage()
        test_name = name.split(".")[0]
        fp, pathname, description = imp.find_module(test_name,
                                            [config.main.testdir])
        module = imp.load_module(name, fp, pathname, description)

        try:
            test.name = module.__name__
            test.desc = module.__desc__
            test.module = module
        except:
            test.name = test_name
            test.desc = ""
            test.module = module

        return test_name, test

    return None, None

