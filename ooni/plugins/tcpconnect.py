"""
This is a self genrated test created by scaffolding.py.
you will need to fill it up with all your necessities.
Safe hacking :).
"""
from zope.interface import implements
from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.internet import reactor
from twisted.internet.protocol import Factory, Protocol
from twisted.internet.endpoints import TCP4ClientEndpoint

from ooni.plugoo.tests import ITest, OONITest
from ooni.plugoo.assets import Asset
from ooni import log

class tcpconnectArgs(usage.Options):
    optParameters = [['asset', 'a', None, 'File containing IP:PORT combinations, one per line.'],
                     ['resume', 'r', 0, 'Resume at this index']]

class tcpconnectTest(OONITest):
    implements(IPlugin, ITest)

    shortName = "tcpconnect"
    description = "tcpconnect"
    requirements = None
    options = tcpconnectArgs
    blocking = False

    def experiment(self, args):
        try:
            host, port = args['asset'].split(':')
        except:
            raise Exception("Error in parsing asset. Wrong format?")
        class DummyFactory(Factory):
            def buildProtocol(self, addr):
                return Protocol()

        def gotProtocol(p):
            p.transport.loseConnection()
            log.msg("Got a connection!")
            log.msg(str(p))
            return {'result': True, 'target': [host, port]}

        def gotError(err):
            log.msg("Had error :(")
            log.msg(err)
            return {'result': False, 'target': [host, port]}

        # What you return here gets handed as input to control
        point = TCP4ClientEndpoint(reactor, host, int(port))
        d = point.connect(DummyFactory())
        d.addCallback(gotProtocol)
        d.addErrback(gotError)
        return d

    def load_assets(self):
        if self.local_options:
            return {'asset': Asset(self.local_options['asset'])}
        else:
            return {}

# We need to instantiate it otherwise getPlugins does not detect it
# XXX Find a way to load plugins without instantiating them.
tcpconnect = tcpconnectTest(None, None, None)
