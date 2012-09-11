#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# 
#  +-----------+
#  |  BRIDGET  |
#  |        +----------------------------------------------+
#  +--------| Use a slave Tor process to test making a Tor |
#           | connection to a list of bridges or relays.   |
#           +----------------------------------------------+
#
# :authors: Arturo Filasto, Isis Lovecruft
# :licence: see included LICENSE
# :version: 0.1.0-alpha

from __future__             import with_statement
from zope.interface         import implements
from twisted.python         import usage
from twisted.plugin         import IPlugin
from twisted.internet       import reactor, error

import random

try:
    from ooni.lib.txtorcon  import CircuitListenerMixin, IStreamAttacher
except:
    print "BridgeT requires txtorcon: https://github.com/meejah/txtorcon.git"
    print "Your copy of OONI should have it included, if you're seeing this"
    print "message, please file a bug report."
    log.msg ("Bridget: Unable to import from ooni.lib.txtorcon")

from ooni.utils             import log
from ooni.plugoo.tests      import ITest, OONITest
from ooni.plugoo.assets     import Asset


class BridgetArgs(usage.Options):
    optParameters = [
        ['bridges', 'b', None, 
         'List of bridges to scan (IP:ORport)'],
        ['relays', 'f', None, 
         'List of relays to scan (IP)'],
        ['socks', 's', 9049,
         'Tor SocksPort to use'],
        ['control', 'c', 9052, 
         'Tor ControlPort to use'],
        ['random', 'x', False, 
         'Randomize control and socks ports'],
        ['tor-path', 'p', '/usr/sbin/tor',
         'Path to the Tor binary to use'],
        ['transport', 't', None, 
         'Tor ClientTransportPlugin string. Requires -b.'],
        ['resume', 'r', 0, 
         'Resume at this index']]

class CustomCircuit(CircuitListenerMixin):
    implements(IStreamAttacher)

    from txtorcon.interface import IRouterContainer, ICircuitContainer

    def __init__(self, state):
        self.state = state
        self.waiting_circuits = []
        
    def waiting_on(self, circuit):
        for (circid, d) in self.waiting_circuits:
            if circuit.id == circid:
                return true
        return False

    def circuit_extend(self, circuit, router):
        "ICircuitListener"
        if circuit.purpose != 'GENERAL':
            return
        if self.waiting_on(circuit):
            log.msg("Circuit %d (%s)" % (circuit.id, router.id_hex))
            
    def circuit_built(self, circuit):
        "ICircuitListener"
        if circuit.purpose != 'GENERAL':
            return
        
        log.msg("Circuit %s built ..." % circuit.id)
        log.msg("Full path of %s: %s" % (circuit.id, circuit.path))

        for (circid, d) in self.waiting_circuits:
            if circid == circuit.id:
                self.waiting_circuits.remove(circid, d)
                d.callback(circuit)

    def circuit_failed(self, circuit, reason):
        if self.waiting_on(circuit):
            log.msg("A circuit we requested %s failed for reason %s" %
                    (circuit.id, reason))
            circid, d = None, None
            for x in self.waiting_circuits:
                if x[0] == circuit.id:
                    circid, d, stream_cc = x
            if d is None:
                raise Exception("Expected to find circuit.")

            self.waiting_circuits.remove((circid, d))
            log.msg("Trying to build a circuit for %s" % circid)
            self.request_circuit_build(d)

    def check_circuit_route(self, circuit, router):
        if router in circuit.path:
            #router.update() ## XXX can i use without args? no.
            TorInfo.dump(self)

    def request_circuit_build(self, deferred):
        entries = self.state.entry_guards.value()
        relays  = self.state.routers.values()

        log.msg("We have these nodes listed as entry guards:") 
        log.msg("%s" % entries)
        log.msg("We have these nodes listed as relays:")
        log.msg("%s" % relays)

        path = [random.choice(entries),
                random.choice(relays),
                random.choice(relays)]

        log.msg("Requesting a circuit: %s" 
                % '-->'.join(map(lambda x: x.location.countrycode, path)))
        
        class AppendWaiting:
            def __init__(self, attacher, deferred):
                self.attacher = attacher
                self.d        = deferred

            def __call__(self, circuit):
                """
                Return from build_circuit is a Circuit, however, we want to
                wait until it is built before we can issue an attach on it and
                callback to the Deferred we issue here.
                """
                log.msg("Circuit %s is in progress ..." % circuit.id)
                self.attacher.waiting_circuits.append((circuit.id, self.d))

        return self.state.build_circuit(path).addCallback(AppendWaiting(self, deferred_to_callback)).addErrback(log.err)

class BridgetTest(OONITest):
    """
    XXX fill me in

    :ivar config: 
        An :class:`ooni.lib.txtorcon.TorConfig` instance.
    :ivar use_bridges:
        A boolean integer [0|1]. 
    :ivar entry_nodes:
        A string of all provided relays to test. We have to do this
        because txtorcon.TorState().entry_guards won't build a custom
        circuit if the first hop isn't in the torrc's EntryNodes.
    :ivar relay_list:
        The same as :ivar entry_nodes: but in list form.
    :ivar socks_port:
        Integer for Tor's SocksPort.
    :ivar control_port:
        Integer for Tor's ControlPort.
    :ivar plug_transport:
        String defining the Tor's ClientTransportPlugin, for testing 
        a bridge's pluggable transport functionality.
    :ivar tor_binary:
        Path to the Tor binary to use, e.g. \'/usr/sbin/tor\'
    """
    implements(IPlugin, ITest)

    shortName = "bridget"
    description = "Use a Tor process to test connecting to bridges/relays"
    requirements = None
    options = BridgetArgs
    blocking = False

    def load_assets(self):
        """
        Load bridges from file given in user options. Bridges should be given
        in the form IP:ORport. We don't want to load relays as assets, because
        it's inefficient to test them one at a time.
        """
        assets = {}
        if self.local_options:
            if self.local_options['bridges']:
                assets.update({'bridge': Asset(self.local_options['bridges'])})
        return assets

    def initialize(self):
        """
        Extra initialization steps. We only want one child Tor process
        running, so we need to deal with the creation of the torrc only once,
        before the experiment runs.
        """
        self.relay_list     = []
        ## XXX why doesn't the default set in the options work?
        self.socks_port     = 9049
        self.control_port   = 9052

        if self.local_options:
            try:
                from ooni.lib.txtorcon import TorConfig
            except:
                log.msg("Could not import TorConfig class from txtorcon")
                raise

            options             = self.local_options
            self.config         = TorConfig()
            self.socks_port     = options['socks']
            self.control_port   = options['control']

            if options['bridges']:
                log.msg("Using Bridges ...")
                self.config.UseBridges = 1
                
            if options['relays']:
                '''
                Stupid hack for when testing only relays (and not bridges):
                Tor doesn't use EntryNodes when UseBridges is enabled, but
                txtorcon requires config.state.entry_guards to make a custom
                circuit, so we should list them as EntryNodes anyway.
                '''
                log.msg("Using relays ...")

                with open(options['relays']) as relay_file:
                    for line in relay_file.readlines():
                        if line.startswith('#'):
                            continue
                        else:
                            relay = line.replace('\n', '') ## not assets because
                            self.relay_list.append(relay)  ## we don't want to 
                                                           ## test one at a time
                        self.config.EntryNodes = ','
                        self.config.EntryNodes.join(relay_list)

            if options['random']:
                log.msg("Using randomized ControlPort and SocksPort ...")
                self.socks_port   = random.randint(1024, 2**16)
                self.control_port = random.randint(1024, 2**16)

            if options['tor-path']:
                self.tor_binary = options['tor-path']

            if options['transport']:
                '''
                ClientTransportPlugin transport socks4|socks5 IP:PORT
                ClientTransportPlugin transport exec path-to-binary [options]
                '''
                if not options['bridges']:
                    e = "To test pluggable transports, you must provide a file"
                    e = e+"with a list of bridge IP:ORPorts. See \'-b' option."
                    raise usage.UsageError("%s" % e)
                    
                log.msg("Using pluggable transport ...")
                ## XXX fixme there's got to be a better way to check the exec
                assert type(options['transport']) is str
                self.config.ClientTransportPlugin = options['transport']

            self.config.SocksPort   = self.socks_port
            self.config.ControlPort = self.control_port
            self.config.save()

            print self.config.create_torrc()
            report = {'tor_config': self.config.config}
            #log.msg("Starting Tor")
            #
            #self.tor_process_protocol = self.bootstrap_tor(self.config)
            #self.d = self.bootstrap_tor(self.d, self.config, 
            #                            self.reactor, self.report)
            #return self.d
            return self.config
        else:
            return None

    def bootstrap_tor(self, config, args):
        """
        Launch a Tor process with the TorConfig instance returned from
        initialize().

        Returns a Deferred which callbacks with a TorProcessProtocol connected
        to the fully-bootstrapped Tor; this has a txtorcon.TorControlProtocol
        instance as .protocol.
        """
        from ooni.lib.txtorcon import TorProtocolFactory, TorConfig, TorState
        from ooni.lib.txtorcon import DEFAULT_VALUE, launch_tor

        log.msg("Tor config: %s" % config)
        log.msg("Starting Tor ...")        

        def setup_failed(args):
            log.msg("Setup Failed.")
            report.update({'failed': args})
            reactor.stop()

        def setup_complete(proto):
            log.msg("Setup Complete: %s" % proto)
            state = TorState(proto.tor_protocol)
            state.post_bootstrap.addCallback(state_complete).addErrback(setup_failed)
            report.update({'success': args})

        def bootstrap(c):
            conf = TorConfig(c)
            conf.post_bootstrap.addCallback(setup_complete).addErrback(setup_failed)
            log.msg("Tor process connected, bootstrapping ...")

        def updates(prog, tag, summary):
            log.msg("%d%%: %s" % (prog, summary))

        ## :return: a Deferred which callbacks with a TorProcessProtocol
        ##          connected to the fully-bootstrapped Tor; this has a 
        ##          txtorcon.TorControlProtocol instance as .protocol.
        deferred = launch_tor(config, reactor, progress_updates=updates,
                              tor_binary=self.tor_binary)
        deferred.addCallback(bootstrap, config)
        deferred.addErrback(setup_failed)

        #print "Tor process ID: %s" % d.transport.pid
        return deferred

    def experiment(self, args):
        """
        XXX fill me in
        """
        log.msg("BridgeT: initiating test ... ")

        def reconfigure_failed(args):

        def reconfigure_controller(proto, args):
            ## if bridges and relays, use one bridge then build a circuit 
            ## from the relays
            if args['bridge']:
                print args
                print args['bridge']
                #d.addCallback(CustomCircuit(state))
                proto.set_conf('Bridge', args['bridge'])
            ## if bridges only, try one bridge at a time, but don't build
            ## circuits, just return
            ## if relays only, build circuits from relays
        
        ## XXX see txtorcon.TorControlProtocol.add_event_listener
        ## we may not need full CustomCircuit class

        d = defer.Deferred() ## 1 make deferred
        d.addCallback(self.bootstrap_tor, self.config) ## 2 blastoff
          ## 3 reconfigure
          ## 4 build circuits
        
        #d = self.bootstrap_tor(self.config, args).addCallback(configure,
        ##c = CustomCircuit(state)
        #d.addCallback(configure, d.protocol)
        #d.addErrback(err)
        #return d

## So that getPlugins() can register the Test:
bridget = BridgetTest(None, None, None)

## ISIS' NOTES
## 
## 
## 
