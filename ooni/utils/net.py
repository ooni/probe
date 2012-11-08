# -*- encoding: utf-8 -*-
#
# net.py
# --------
# OONI utilities for network infrastructure and hardware.
#
# :authors: Isis Lovecruft, Arturo Filasto
# :version: 0.0.1-pre-alpha
# :license: (c) 2012 Isis Lovecruft, Arturo Filasto
#           see attached LICENCE file

def getClientAddress():
    address = {'asn': 'REPLACE_ME',
               'ip': 'REPLACE_ME'}
    return address

def capturePackets():
    from scapy.all import sniff
    sniff()

class PermissionsError(SystemExit):
    def __init__(self, *args, **kwargs):
        if not args and not kwargs:
            pe = "This test requires admin or root privileges to run. Exiting..."
            super(PermissionsError, self).__init__(pe, *args, **kwargs)
        else:
            super(PermissionsError, self).__init__(*args, **kwargs)

class IfaceError(SystemExit):
    def __init__(self, *args, **kwargs):
        super(IfaceError, self).__init__(*args, **kwargs)
