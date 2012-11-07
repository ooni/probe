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
import sys

from twisted.internet  import defer
from zope.interface    import implements

from txtorcon          import CircuitListenerMixin, IStreamAttacher
from txtorcon          import TorState, TorConfig
from ooni.utils        import log
from ooni.utils.timer  import deferred_timeout, TimeoutError

# XXX This can be refactored to os.path.abspath
# os.path.abspath(path)
# Return a normalized absolutized version of the pathname path. On most
# platforms, this is equivalent to normpath(join(os.getcwd(), path)).
def parse_data_dir(data_dir):
    """
    Parse a string that a has been given as a DataDirectory and determine
    its absolute path on the filesystem.

    :param data_dir:
        A directory for Tor's DataDirectory, to be parsed.
    :return:
        The absolute path of :param:data_dir.
    """
    from os import path, getcwd
    import sys

    try:
        assert isinstance(data_dir, str), \
            "Parameter type(data_dir) must be str"
    except AssertionError, ae:
        log.err(ae)

    if data_dir.startswith('~'):
        data_dir = path.expanduser(data_dir)
    elif data_dir.startswith('/'):
        data_dir = path.join(getcwd(), data_dir)
    elif data_dir.startswith('./'):
        data_dir = path.abspath(data_dir)
    else:
        data_dir = path.join(getcwd(), data_dir)

    try:
        assert path.isdir(data_dir), "Could not find %s" % data_dir
    except AssertionError, ae:
        log.err(ae)
        sys.exit()
    else:
        return data_dir

# XXX txtorcon handles this already.
# Also this function is called write_torrc but it has hardcoded inside of it
# bridget-tordata.
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
                list.remove(item)
            except ValueError, ve:
                log.err(ve)

def remove_public_relays(state, bridges):
    """
    Remove bridges from our bridge list which are also listed as public
    relays. This must be called after Tor has fully bootstrapped and we have a
    :class:`ooni.lib.txtorcon.TorState` with the
    :attr:`ooni.lib.txtorcon.TorState.routers` attribute assigned.

    XXX Does state.router.values() have all of the relays in the consensus, or
    just the ones we know about so far?

    XXX FIXME: There is a problem in that Tor needs a Bridge line to already be
    configured in order to bootstrap. However, after bootstrapping, we grab the
    microdescriptors of all the relays and check if any of our bridges are
    listed as public relays. Because of this, the first bridge does not get
    checked for being a relay.
    """
    IPs = map(lambda addr: addr.split(':',1)[0], bridges['all'])
    both = set(state.routers.values()).intersection(IPs)

    if len(both) > 0:
        try:
            updated = map(lambda node: remove_node_from_list(node), both)
            log.debug("Bridges in both: %s" % both)
            log.debug("Updated = %s" % updated)
            #if not updated:
            #    defer.returnValue(state)
            #else:
            #    defer.returnValue(state)
            return state
        except Exception, e:
            log.err("Removing public relays %s from bridge list failed:\n%s"
                    % (both, e))

# XXX It is unclear to me how all of these functions would be reused. Why must
# hey be inside of a module?
def setup_done(proto):
    log.msg("Setup Complete")
    state = TorState(proto.tor_protocol)
    state.post_bootstrap.addCallback(state_complete)
    state.post_bootstrap.addErrback(setup_fail)


def setup_fail(proto):
    log.msg("Setup Failed:\n%s" % proto)
    return proto
    #reactor.stop()

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

# XXX txtorcon does this already for us.
def start_tor(reactor, config, control_port, tor_binary, data_dir,
              report=None, progress=updates,
              process_cb=None, process_eb=None):
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
        The class:`ooni.plugoo.reports.Report` instance.
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

    if process_cb is not None and process_eb is not None:
        process_protocol.connected_cb.addCallbacks(process_cb, process_eb)

    reactor.addSystemEventTrigger('before', 'shutdown',
                                  partial(delete_files_or_dirs, to_delete))
    try:
        transport = reactor.spawnProcess(process_protocol,
                                         tor_binary,
                                         args=(tor_binary,'-f',torrc),
                                         env={'HOME': data_dir},
                                         path=data_dir)
        transport.closeStdin()
    except RuntimeError, e:
       log.err("Starting Tor failed:")
       process_protocol.connected_cb.errback(e)
    except NotImplementedError, e:
       url = "http://starship.python.net/crew/mhammond/win32/Downloads.html"
       log.msg("Running bridget on Windows requires pywin32: %s" % url)
       process_protocol.connected_cb.errback(e)

    return process_protocol.connected_cb

@defer.inlineCallbacks
def start_tor_filter_nodes(reactor, config, control_port, tor_binary,
                              data_dir, bridges):
    """
    Bootstrap a Tor process and return a fully-setup
    :class:`ooni.lib.txtorcon.TorState`. Then search for our bridges
    to test in the list of known public relays,
    :ivar:`ooni.lib.txtorcon.TorState.routers`, and remove any bridges
    which are known public relays.

    :param reactor:
        The :class:`twisted.internet.reactor`.
    :param config:
        An instance of :class:`ooni.lib.txtorcon.TorConfig`.
    :param control_port:
        The port to use for Tor's ControlPort. If already configured in
        the TorConfig instance, this can be given as
        TorConfig.config.ControlPort.
    :param tor_binary:
        The full path to the Tor binary to execute.
    :param data_dir:
        The full path to the directory to use as Tor's DataDirectory.
    :param bridges:
        A dictionary which has a key 'all' which is a list of bridges to
        test connecting to, e.g.:
             bridges['all'] = ['1.1.1.1:443', '22.22.22.22:9001']
    :return:
        A fully initialized :class:`ooni.lib.txtorcon.TorState`.
    """
    setup = yield start_tor(reactor, config, control_port,
                            tor_binary, data_dir,
                            process_cb=setup_done, process_eb=setup_fail)
    filter_nodes = yield remove_public_relays(setup, bridges)
    defer.returnValue(filter_nodes)

# XXX Why is this needed?
@defer.inlineCallbacks
def start_tor_with_timer(reactor, config, control_port, tor_binary, data_dir,
                         bridges, timeout):
    """
    Start bootstrapping a Tor process wrapped with an instance of the class
    decorator :func:`ooni.utils.timer.deferred_timeout` and complete callbacks
    to either :func:`setup_done` or :func:`setup_fail`. Return a fully-setup
    :class:`ooni.lib.txtorcon.TorState`. Then search for our bridges to test
    in the list of known public relays,
    :ivar:`ooni.lib.txtorcon.TorState.routers`, and remove any bridges which
    are listed as known public relays.

    :param reactor:
        The :class:`twisted.internet.reactor`.
    :param config:
        An instance of :class:`ooni.lib.txtorcon.TorConfig`.
    :param control_port:
        The port to use for Tor's ControlPort. If already configured in
        the TorConfig instance, this can be given as
        TorConfig.config.ControlPort.
    :param tor_binary:
        The full path to the Tor binary to execute.
    :param data_dir:
        The full path to the directory to use as Tor's DataDirectory.
    :param bridges:
        A dictionary which has a key 'all' which is a list of bridges to
        test connecting to, e.g.:
             bridges['all'] = ['1.1.1.1:443', '22.22.22.22:9001']
    :param timeout:
        The number of seconds to attempt to bootstrap the Tor process before
        raising a :class:`ooni.utils.timer.TimeoutError`.
    :return:
        If the timeout limit is not exceeded, return a fully initialized
        :class:`ooni.lib.txtorcon.TorState`, else return None.
    """
    error_msg = "Bootstrapping has exceeded the timeout limit..."
    with_timeout = deferred_timeout(timeout, e=error_msg)(start_tor)
    try:
        setup = yield with_timeout(reactor, config, control_port, tor_binary,
                                   data_dir, process_cb=setup_done,
                                   process_eb=setup_fail)
    except TimeoutError, te:
        log.err(te)
        defer.returnValue(None)
    #except Exception, e:
    #    log.err(e)
    #    defer.returnValue(None)
    else:
        state = yield remove_public_relays(setup, bridges)
        defer.returnValue(state)

# XXX This is a copy and paste of the above class with just an extra argument.
@defer.inlineCallbacks
def start_tor_filter_nodes_with_timer(reactor, config, control_port,
                                      tor_binary, data_dir, bridges, timeout):
    """
    Start bootstrapping a Tor process wrapped with an instance of the class
    decorator :func:`ooni.utils.timer.deferred_timeout` and complete callbacks
    to either :func:`setup_done` or :func:`setup_fail`. Then, filter our list
    of bridges to remove known public relays by calling back to
    :func:`remove_public_relays`. Return a fully-setup
    :class:`ooni.lib.txtorcon.TorState`. Then search for our bridges to test
    in the list of known public relays,
    :ivar:`ooni.lib.txtorcon.TorState.routers`, and remove any bridges which
    are listed as known public relays.

    :param reactor:
        The :class:`twisted.internet.reactor`.
    :param config:
        An instance of :class:`ooni.lib.txtorcon.TorConfig`.
    :param control_port:
        The port to use for Tor's ControlPort. If already configured in
        the TorConfig instance, this can be given as
        TorConfig.config.ControlPort.
    :param tor_binary:
        The full path to the Tor binary to execute.
    :param data_dir:
        The full path to the directory to use as Tor's DataDirectory.
    :param bridges:
        A dictionary which has a key 'all' which is a list of bridges to
        test connecting to, e.g.:
             bridges['all'] = ['1.1.1.1:443', '22.22.22.22:9001']
    :param timeout:
        The number of seconds to attempt to bootstrap the Tor process before
        raising a :class:`ooni.utils.timer.TimeoutError`.
    :return:
        If the timeout limit is not exceeded, return a fully initialized
        :class:`ooni.lib.txtorcon.TorState`, else return None.
    """
    error_msg = "Bootstrapping has exceeded the timeout limit..."
    with_timeout = deferred_timeout(timeout, e=error_msg)(start_tor_filter_nodes)
    try:
        state = yield with_timeout(reactor, config, control_port,
                                   tor_binary, data_dir, bridges)
    except TimeoutError, te:
        log.err(te)
        defer.returnValue(None)
    #except Exception, e:
    #    log.err(e)
    #    defer.returnValue(None)
    else:
        defer.returnValue(state)

class CustomCircuit(CircuitListenerMixin):
    """
    Utility class for controlling circuit building. See
    'attach_streams_by_country.py' in the txtorcon documentation.

    :param state:
        A fully bootstrapped instance of :class:`ooni.lib.txtorcon.TorState`.
    :param relays:
        A dictionary containing a key 'all', which is a list of relays to
        test connecting to.
    :ivar waiting_circuits:
        The list of circuits which we are waiting to attach to. You shouldn't
        need to touch this.
    """
    # XXX
    # 14:57 < meejah> to build a custom circuit (with no streams) in txtorcon,
    # call TorState.build_circuit -- the Deferred callbacks with the circid

    implements(IStreamAttacher)

    def __init__(self, state, relays=None):
        self.state = state
        self.waiting_circuits = []
        self.relays = relays

    def waiting_on(self, circuit):
        """
        Whether or not we are waiting on the given circuit before attaching to
        it.

        :param circuit:
            An item from :ivar:`ooni.lib.txtorcon.TorState.circuits`.
        :return:
            True if we are waiting on the circuit, False if not waiting.
        """
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
        """
        If building a circuit has failed, try to remove it from our list of
        :ivar:`waiting_circuits`, else request to build it.

        :param circuit:
            An item from :ivar:`ooni.lib.txtorcon.TorState.circuits`.
        :param reason:
            A :class:`twisted.python.fail.Failure` instance.
        :return:
            None
        """
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

        :param router:
            An item from the list
            :func:`ooni.lib.txtorcon.TorState.routers.values()`.
        """
        for circ in self.state.circuits.values():
            if router in circ.path:
            #router.update() ## XXX can i use without args? no.
                TorInfo.dump(self)

    def request_circuit_build(self, deferred, path=None):
        """
        Request a custom circuit.

        :param deferred:
            A :class:`twisted.internet.defer.Deferred` for this circuit.
        :param path:
            A list of router ids to build a circuit from. The length of this
            list must be at least three.
        """
        if path is None:

            pick   = self.relays['all'].pop
            n      = self.state.entry_guards.values()
            choose = random.choice

            first, middle, last = (None for i in range(3))

            if self.relays['remaining']() >= 3:
                first, middle, last = (pick() for i in range(3))
            elif self.relays['remaining']() < 3:
                first = choose(n)
                middle = pick()
                if self.relays['remaining'] == 2:
                    middle, last = (pick() for i in range(2))
                elif self.relay['remaining'] == 1:
                    middle = pick()
                    last = choose(n)
                else:
                    log.msg("Qu'est-que fuque?")
            else:
                middle, last = (random.choice(self.state.routers.values())
                                for i in range(2))

            path = [first, middle, last]

        else:
            assert isinstance(path, list), \
                "Circuit path must be a list of relays!"
            assert len(path) >= 3, \
                "Circuit path must be at least three hops!"

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
    """
    Raised when ooni.lib.txtorcon cannot be imported from. Checks our current
    working directory and the path given to see if txtorcon has been
    initialized via /ooni/lib/Makefile.
    """
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

@defer.inlineCallbacks
def __start_tor_with_timer__(reactor, config, control_port, tor_binary,
                             data_dir, bridges=None, relays=None, timeout=None,
                             retry=None):
    """
    A wrapper for :func:`start_tor` which wraps the bootstrapping of a Tor
    process and its connection to a reactor with a
    :class:`twisted.internet.defer.Deferred` class decorator utility,
    :func:`ooni.utils.timer.deferred_timeout`, and a mechanism for resets.

    ## XXX fill me in
    """
    raise NotImplementedError

    class RetryException(Exception):
        pass

    import sys
    from ooni.utils.timer import deferred_timeout, TimeoutError

    def __make_var__(old, default, _type):
        if old is not None:
            assert isinstance(old, _type)
            new = old
        else:
            new = default
        return new

    reactor = reactor
    timeout = __make_var__(timeout, 120, int)
    retry   = __make_var__(retry, 1, int)

    with_timeout = deferred_timeout(timeout)(start_tor)

    @defer.inlineCallbacks
    def __start_tor__(rc=reactor, cf=config, cp=control_port, tb=tor_binary,
                      dd=data_dir, br=bridges, rl=relays, cb=setup_done,
                      eb=setup_fail, af=remove_public_relays, retry=retry):
        try:
            setup = yield with_timeout(rc,cf,cp,tb,dd)
        except TimeoutError:
            retry -= 1
            defer.returnValue(retry)
        else:
            if setup.callback:
                setup = yield cb(setup)
            elif setup.errback:
                setup = yield eb(setup)
            else:
                setup = setup

            if br is not None:
                state = af(setup,br)
            else:
                state = setup
            defer.returnValue(state)

    @defer.inlineCallbacks
    def __try_until__(tries):
        result = yield __start_tor__()
        try:
            assert isinstance(result, int)
        except AssertionError:
            defer.returnValue(result)
        else:
            if result >= 0:
                tried = yield __try_until__(result)
                defer.returnValue(tried)
            else:
                raise RetryException
    try:
        tried = yield __try_until__(retry)
    except RetryException:
        log.msg("All retry attempts to bootstrap Tor have timed out.")
        log.msg("Exiting ...")
        defer.returnValue(sys.exit())
    else:
        defer.returnValue(tried)

