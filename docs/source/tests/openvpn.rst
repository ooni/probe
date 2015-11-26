Details
=======

*Test Name*: OpenVPN

*Current version*: 0.1

*NetTest*: OpenVPN (https://github.com/TheTorProject/ooni-probe/blob/master/ooni/nettests/third_party/openvpn.py)

*Test Helper*: None

*Test Type*: third party

*Requires Root*: Yes

Description
===========

This test first launches OpenVPN and parses output to determine if it has bootstrapped. After bootstrap, it fetches the  URL specified by the --url argument using OpenVPN.

The specific string used to determine bootstrap from OpenVPN output in version
"0.0.1" is "Initialization Sequence Completed" from standard output.

How to run the test
===================

First get credentials for a OpenVPN service and create the configuration file for OpenVPN. 
An example:

    client
    dev tun
    proto tcp
    remote <vpndomain> 80
    remote <vppnip> 80
    resolv-retry infinite
    tun-mtu 1500
    key-direction 1
    nobind
    persist-key
    persist-tun
    ns-cert-type server
    comp-lzo
    verb 3
    auth-user-pass <vpnuserandpasswordfile>
    route-method exe
    route-delay 2

    <ca>
    -----BEGIN CERTIFICATE-----
    ...
    -----END CERTIFICATE-----
    </ca>
    <tls-auth>
    -----BEGIN OpenVPN Static key V1-----
    ...
    -----END OpenVPN Static key V1-----
    </tls-auth>

To run the test:

`ooniprobe third_party/openvpn -u http://<url>/ -c <OpenVPN configuration file>`

How to install OpenVPN
===================

Run the install script:

`scripts/openvpn_install.sh`

To run OpenVPN manually, :

`openvpn --config <OpenVPN configuration file>`

Sample report
=============

`ooniprobe blocking/http_requests -f example_inputs/url_lists_file.txt`

    ::

    ###########################################
    # OONI Probe Report for openvpn_client_test (0.0.2)
    # Thu Nov 19 12:16:35 2015
    ###########################################
    ---
    input_hashes: []
    options: [-c, openvpn-config.ovpn, -u, '']
    probe_asn: AS0
    probe_cc: ZZ
    probe_city: null
    probe_ip: 127.0.0.1
    report_id: oVWw3KA3UH2XrOlLa8gRaUB1ocvn6LhMeTBOtU1yFMtdyM3L6Bg9ix1ulSWZCGtK
    software_name: ooniprobe
    software_version: 1.3.1
    start_time: 1447928194.0
    test_helpers: {}
    test_name: openvpn_client_test
    test_version: 0.0.2
    ...
    ---
    /usr/sbin/openvpn --config openvpn-config.ovpn: {
      exit_reason: process_done, stderr: '', stdout: 'Thu Nov 19 12:16:35 2015 OpenVPN
        2.3.2 x86_64-pc-linux-gnu [SSL (OpenSSL)] [LZO] [EPOLL] [PKCS11] [eurephia] [MH]
        [IPv6] built on Dec  1 2014

        Thu Nov 19 12:16:35 2015 WARNING: file ''/tmp/openvpn.txt'' is group or others
        accessible

        Thu Nov 19 12:16:35 2015 Control Channel Authentication: tls-auth using INLINE
        static key file

        Thu Nov 19 12:16:35 2015 Attempting to establish TCP connection with [AF_INET]10.100.0.1:993
        [nonblock]

        Thu Nov 19 12:16:37 2015 TCP connection established with [AF_INET]10.100.0.1:993

        Thu Nov 19 12:16:37 2015 TCPv4_CLIENT link local: [undef]

        Thu Nov 19 12:16:37 2015 TCPv4_CLIENT link remote: [AF_INET]10.100.0.1:993

        Thu Nov 19 12:16:39 2015 WARNING: this configuration may cache passwords in memory
        -- use the auth-nocache option to prevent this

        Thu Nov 19 12:16:42 2015 [server] Peer Connection Initiated with [AF_INET]10.100.0.1:993

        Thu Nov 19 12:16:44 2015 Options error: Unrecognized option or missing parameter(s)
        in [PUSH-OPTIONS]:3: dhcp (2.3.2)

        Thu Nov 19 12:16:44 2015 TUN/TAP device tun0 opened

        Thu Nov 19 12:16:44 2015 do_ifconfig, tt->ipv6=0, tt->did_ifconfig_ipv6_setup=0

        Thu Nov 19 12:16:44 2015 /sbin/ip link set dev tun0 up mtu 1500

        Thu Nov 19 12:16:44 2015 /sbin/ip addr add dev tun0 local 10.10.0.54 peer 10.10.0.53

        Thu Nov 19 12:16:44 2015 Initialization Sequence Completed

        '}
    body: "<HTML><HEAD><meta http-equiv=\"content-type\" content=\"text/html;charset=utf-8\"\
      >\n<TITLE>302 Moved</TITLE></HEAD><BODY>\n<H1>302 Moved</H1>\nThe document has moved\n\
      <A HREF=\"http://www.google.de/?gfe_rd=cr&amp;ei=yq9NVsq5JYvZ8Ae58KHoDA\">here</A>.\r\
      \n</BODY></HTML>\r\n"
    input: null
    success: true
    test_runtime: 9.549253940582275
    test_start_time: 1447928195.0
    ...
