#
# onion.py
# ----------
# Utilities for working with Tor.
#
# This code is largely taken from txtorcon and its documentation, and as such
# any and all credit should go to Meejah. Minor adjustments have been made to
# use OONI's logging system, and to build custom circuits without actually
# attaching streams.
#
# :author: Meejah, Isis Lovecruft
# :license: see included LICENSE file
# :copyright: copyright (c) 2012 The Tor Project, Inc.
# :version: 0.1.0-alpha
#
# XXX TODO add report keys for onion methods

import random

from ooni.lib.txtorcon import CircuitListenerMixin, IStreamAttacher
from ooni.lib.txtorcon import TorState
from ooni.utils        import log
from twisted.internet  import defer
from zope.interface    import implements


def setup_done(proto):
    log.msg("Setup Complete")
    state = TorState(proto.tor_protocol)
    state.post_bootstrap.addCallback(state_complete)
    state.post_bootstrap.addErrback(setup_fail)

def setup_fail(proto):
    log.err("Setup Failed: %s" % proto)
    #report.update({'setup_fail': proto})
    reactor.stop()

def state_complete(state):
    """Called when we've got a TorState."""
    log.msg("We've completely booted up a Tor version %s at PID %d"
            % (state.protocol.version, state.tor_pid))
    log.msg("This Tor has the following %d Circuits:"
            % len(state.circuits))
    for circ in state.circuits.values():
        log.msg("%s" % circ)
    return state

def updates(_progress, _tag, _summary):
    """Log updates on the Tor bootstrapping process.""" 
    log.msg("%d%%: %s" % (_progress, _summary))

def bootstrap(ctrl):
    """
    Bootstrap Tor from an instance of
    :class:`ooni.lib.txtorcon.TorControlProtocol`.
    """
    conf = TorConfig(ctrl)
    conf.post_bootstrap.addCallback(setup_done).addErrback(setup_fail)
    log.msg("Tor process connected, bootstrapping ...")

def parse_data_dir(data_dir):
    """
    Parse a string that a has been given as a DataDirectory and determine
    its absolute path on the filesystem.
    
    :param data_dir:
        A directory for Tor's DataDirectory, to be parsed.
    :return:
        The absolute path of :param:data_dir.
    """
    import os

    if data_dir.startswith('~'):
        data_dir = os.path.expanduser(data_dir)
    elif data_dir.startswith('/'):
        data_dir = os.path.join(os.getcwd(), data_dir)
    elif data_dir.startswith('./'):
        data_dir = os.path.abspath(data_dir)
    else:
        data_dir = os.path.join(os.getcwd(), data_dir)
    return data_dir

def write_torrc(conf, data_dir=None):
    """
    Create a torrc in our data_dir. If we don't yet have a data_dir, create a
    temporary one. Any temporary files or folders are added to delete_list.
    
    :param conf:
        A :class:`ooni.lib.txtorcon.TorConfig` object, with all configuration
        values saved.
    :param data_dir:
        The Tor DataDirectory to use.
    :return: torrc, data_dir, delete_list
    """
    try:
        from os       import write, close
        from tempfile import mkstemp, mkdtemp
    except ImportError, ie:
        log.err(ie)

    delete_list = []
    
    if data_dir is None:
        data_dir = mkdtemp(prefix='bridget-tordata')
        delete_list.append(data_dir)
    conf.DataDirectory = data_dir
    
    (fd, torrc) = mkstemp(dir=data_dir)
    delete_list.append(torrc)
    write(fd, conf.create_torrc())
    close(fd)

    return torrc, data_dir, delete_list

def delete_files_or_dirs(delete_list):
    """
    Given a list of files or directories to delete, delete all and suppress
    all errors.

    :param delete_list:
        A list of files or directories to delete.
    """
    try:
        from os     import unlink
        from shutil import rmtree
    except ImportError, ie:
        log.err(ie)

    for temp in delete_list:
        try:
            unlink(temp)
        except OSError:
            rmtree(temp, ignore_errors=True)

def remove_node_from_list(node, list):
    for item in list:              ## bridges don't match completely
        if item.startswith(node):  ## due to the :<port>.
            try:
                log.msg("Removing %s because it is a public relay" % node)
                list.remove(line)
            except ValueError, ve:
                log.err(ve)

@defer.inlineCallbacks
def remove_public_relays(state, bridges):
    """
    Remove bridges from our bridge list which are also listed as public
    relays. This must be called after Tor has fully bootstrapped and we have a
    :class:`ooni.lib.txtorcon.TorState` with the
    :attr:`ooni.lib.txtorcon.TorState.routers` attribute assigned.

    XXX Does state.router.values() have all of the relays in the consensus, or
    just the ones we know about so far?
    """
    IPs = map(lambda addr: addr.split(':',1)[0], bridges)
    both = set(state.routers.values()).intersection(IPs)

    if len(both) > 0:
        try:
            updated = yield map(lambda node: remove_node_from_list(node), 
                                both)
            if not updated:
                ## XXX do these need to be state.callback?
                defer.returnValue(state)
            else:
                defer.returnValue(state)
        except Exception, e:
            log.msg("Removing public relays from bridge list failed:\n%s"
                    % both)
            log.err(e)
        except ValueError, ve:
            log.err(ve)

#@defer.inlineCallbacks
def start_tor(reactor, config, control_port, tor_binary, data_dir,
              report=None, progress=updates, process_cb=setup_done,
              process_eb=setup_fail):
    """
    Use a txtorcon.TorConfig() instance, config, to write a torrc to a
    tempfile in our DataDirectory, data_dir. If data_dir is None, a temp
    directory will be created. Finally, create a TCP4ClientEndpoint at our
    control_port, and connect it to our reactor and a spawned Tor
    process. Compare with :meth:`txtorcon.launch_tor` for differences.

    :param reactor:
        An instance of class:`twisted.internet.reactor`.
    :param config:
        An instance of class:`txtorcon.TorConfig` with all torrc options
        already configured. ivar:`config.ControlPort`,
        ivar:`config.SocksPort`, ivar:`config.CookieAuthentication`, should
        already be set, as well as ivar:`config.UseBridges` and
        ivar:`config.Bridge` if bridges are to be used.
        ivar:`txtorcon.DataDirectory` does not need to be set.
    :param control_port:
        The port number to use for Tor's ControlPort.
    :param tor_binary:
        The full path to the Tor binary to use.
    :param data_dir:
        The directory to use as Tor's DataDirectory.
    :param report:
        The class:`ooni.plugoo.reports.Report` instance to .update().
    :param progress:
        A non-blocking function to handle bootstrapping updates, which takes
        three parameters: _progress, _tag, and _summary.
    :param process_cb:
        The function to callback to after 
        class:`ooni.lib.txtorcon.TorProcessProtocol` returns with the fully
        bootstrapped Tor process.
    :param process_eb:
        The function to errback to if 
        class:`ooni.lib.txtorcon.TorProcessProtocol` fails.
    :return:
        The result of the callback of a
        class:`ooni.lib.txtorcon.TorProcessProtocol` which callbacks with a
        class:`txtorcon.TorControlProtocol` as .protocol.
    """
    try:
        from functools                  import partial
        from twisted.internet.endpoints import TCP4ClientEndpoint
        from ooni.lib.txtorcon          import TorProtocolFactory
        from ooni.lib.txtorcon          import TorProcessProtocol
    except ImportError, ie:
        log.err(ie)

    ## TODO: add option to specify an already existing torrc, which
    ##       will require prior parsing to enforce necessary lines
    (torrc, data_dir, to_delete) = write_torrc(config, data_dir)

    log.msg("Starting Tor ...")
    log.msg("Using the following as our torrc:\n%s" % config.create_torrc())
    if report is None:
        report = {'torrc': config.create_torrc()}
    else:
        report.update({'torrc': config.create_torrc()})

    end_point = TCP4ClientEndpoint(reactor, 'localhost', control_port)
    connection_creator = partial(end_point.connect, TorProtocolFactory())
    process_protocol = TorProcessProtocol(connection_creator, progress)
    process_protocol.to_delete = to_delete

    reactor.addSystemEventTrigger('before', 'shutdown',
                                  partial(delete_files_or_dirs, to_delete))
    #try:
    #    transport = yield reactor.spawnProcess(process_protocol,
    #                                           tor_binary,
    #                                           args=(tor_binary,'-f',torrc),
    #                                           env={'HOME': data_dir},
    #                                           path=data_dir)
    #    if transport:
    #        transport.closeStdin()
    #except RuntimeError as e:
    #    log.err("Starting Tor failed: %s" % e)
    #    process_protocol.connected_cb.errback(e)
    #except NotImplementedError, e:
    #    url = "http://starship.python.net/crew/mhammond/win32/Downloads.html"
    #    log.err("Running bridget on Windows requires pywin32: %s" % url)
    #    process_protocol.connected_cb.errback(e)
    try:
        transport = reactor.spawnProcess(process_protocol, 
                                         tor_binary, 
                                         args=(tor_binary,'-f',torrc),
                                         path=data_dir)
        transport.closeStdin()
    except RuntimeError, e:
        log.err(e)
        process_protocol.connected_cb.errback(e)

    return process_protocol.connected_cb

    #d = yield process_protocol.connected_cb
    #defer.returnValue(d)
    
class CustomCircuit(CircuitListenerMixin):
    implements(IStreamAttacher)

    def __init__(self, state, relays=None):
        self.state = state
        self.waiting_circuits = []
        self.relays = relays

    def waiting_on(self, circuit):
        for (circid, d) in self.waiting_circuits:
            if circuit.id == circid:
                return True
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
                self.waiting_circuits.remove((circid, d))
                d.callback(circuit)

    def circuit_failed(self, circuit, reason):
        if self.waiting_on(circuit):
            log.msg("Circuit %s failed for reason %s" % (circuit.id, reason))
            circid, d = None, None
            for c in self.waiting_circuits:
                if c[0] == circuit.id:
                    circid, d = c
            if d is None:
                raise Exception("Expected to find circuit.")

            self.waiting_circuits.remove((circid, d))
            log.msg("Trying to build a circuit for %s" % circid)
            self.request_circuit_build(d)

    def check_circuit_route(self, router):
        """
        Check if a relay is a hop in one of our already built circuits. 

        """
        for circ in self.state.circuits.values():
            if router in circuit.path:
            #router.update() ## XXX can i use without args? no.
                TorInfo.dump(self)

    def request_circuit_build(self, deferred, path=None):
        if path is None:
            if self.state.relays_remaining() > 0:
                first, middle,last = (self.state.relays.pop()
                                      for i in range(3))
            else:
                first = random.choice(self.state.entry_guards.values())
                middle, last = (random.choice(self.state.routers.values())
                                for i in range(2))
            path = [first, middle, last]
        else:
            assert type(path) is list, "Circuit path must be a list of relays!"
            assert len(path) >= 3, "Circuits must be at least three hops!"

        log.msg("Requesting a circuit: %s" 
                % '->'.join(map(lambda node: node, path)))

        class AppendWaiting:
            def __init__(self, attacher, deferred):
                self.attacher = attacher
                self.d        = deferred
            def __call__(self, circ):
                """
                Return from build_circuit is a Circuit, however,
                we want to wait until it is built before we can
                issue an attach on it and callback to the Deferred
                we issue here.
                """
                log.msg("Circuit %s is in progress ..." % circ.id)
                self.attacher.waiting_circuits.append((circ.id, self.d))

        return self.state.build_circuit(path).addCallback(
            AppendWaiting(self, deferred)).addErrback(
            log.err)

class TxtorconImportError(ImportError):
    """Raised when /ooni/lib/txtorcon cannot be imported from."""
    from os import getcwd, path

    cwd, tx = getcwd(), 'lib/txtorcon/torconfig.py'
    try:
        log.msg("Unable to import from ooni.lib.txtorcon")
        if cwd.endswith('ooni'):
            check = path.join(cwd, tx)
        elif cwd.endswith('utils'):
            check = path.join(cwd, '../'+tx)
        else:
            check = path.join(cwd, 'ooni/'+tx)
        assert path.isfile(check)
    except:
        log.msg("Error: Some OONI libraries are missing!")
        log.msg("Please go to /ooni/lib/ and do \"make all\"")

class PTNoBridgesException(Exception):
    """Raised when a pluggable transport is specified, but not bridges."""
    def __init__(self):
        log.msg("Pluggable transport requires the bridges option")
        return sys.exit()

class PTNotFoundException(Exception):
    def __init__(self, transport_type):
        m  = "Pluggable Transport type %s was unaccounted " % transport_type
        m += "for, please contact isis(at)torproject(dot)org and it will "
        m += "get included."
        log.msg("%s" % m)
        return sys.exit()

