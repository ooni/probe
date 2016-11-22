The [Open Observatory of Network Interference
(OONI)](https://ooni.torproject.org/) is a free software project, under the [Tor
Project](https://www.torproject.org/), which collects and processes network
measurements with the aim of detecting network anomalies, such as censorship and
traffic manipulation.

Running OONI may be against the terms of service of your ISP or legally
questionable in your country. By running OONI you will connect to web services
which may be banned, and use web censorship circumvention methods such as Tor.
The OONI project will publish data submitted by probes, possibly including your
IP address or other identifying information. In addition, your use of OONI will
be clear to anybody who has access to your computer, and to anybody who can
monitor your internet connection (such as your employer, ISP or government).

By running ooniprobe, you are participating as a volunteer in this project. This
form includes information that you should be aware of and consent to *prior* to
running ooniprobe.

## OONI software tests

The OONI project has developed multiple free software tests which are designed to:

* Detect the blocking of websites

* Detect systems responsible for censorship and traffic manipulation

* Evaluate the reachability of [Tor bridges](https://bridges.torproject.org/),
  proxies, VPNs, and sensitive domains

Below we provide brief descriptions of how these tests work. 

## Test descriptions

The recommended set of tests that users run through the
`oonideckgen` command include the following:

**Web connectivity:** This test examines whether websites are reachable and if
they are not, it attempts to determine whether access to them is blocked through
DNS tampering, TCP connection RST/IP blocking or by having a transparent HTTP
proxy. It does so by identifying the resolver of the user, performing a DNS
lookup, attempting to establish a TCP session and by sending HTTP GET requests
to the servers that are hosting tested websites.

**HTTP invalid request line:** This test tries to detect the presence of network
components (“middle box”) which could be responsible for censorship and/or
traffic manipulation. Instead of sending a normal HTTP request, this test sends
an invalid HTTP request line - containing an invalid HTTP version number, an
invalid field count and a huge request method – to an echo service listening on
the standard HTTP port. If a middle box is present in the tested network, the
invalid HTTP request line will be intercepted by the middle box and this may
trigger error messages which can help identify the proxy technologies.

**HTTP header field manipulation:** This test tries to detect the presence of
network components (“middle box”) which could be responsible for censorship
and/or traffic manipulation. It does so by sending HTTP requests which include
valid, but non-canonical HTTP headers to a backend control server which sends
back any data it receives. If we receive the HTTP headers exactly as we sent
them, then we assume that there is no “middle box” in the network. If,
however, such software is present in the network that we are testing, it will
likely normalize the invalid headers that we are sending or add extra headers.

Another test which attempts to detect traffic manipulation includes **Multi-
protocol traceroute**, which constructs packets in such a way that they perform
a traceroute from multiple protocols and ports simultaneously. Other tests
include **Tor bridge reachability**, **Psiphon**, **Lantern**, **OpenVPN** and
**Meek fronted requests**, which examine whether these services work within a
tested network by attempting to connect to them in an automated way.

Further test descriptions can be found here.

## Risks

Many countries have a lengthy history of subjecting digital rights activists to
various forms of abuse that could make it dangerous for individuals in these
countries to run OONI. The use of OONI might therefore subject users to severe
civil, criminal, or extra-judicial penalties, and such sanctions can potentially
include:

* Imprisonment

* Physical assaults

* Large fines

* Receiving threats

* Being placed on government watch lists

* Targeted for surveillance

While most countries don't have laws which specifically prohibit the use of
network measurement software, it's important to note that the use of OONI can
*still* potentially be criminalized in certain countries under other, broader
laws if, for example, its use is viewed as an illegal or anti-government
activity. OONI users might also face the risk of being criminalized on the
grounds of *national security* if the data obtained and published by running
OONI is viewed as "jeopardizing" the country's external or internal security. In
extreme cases, any form of active network measurement could be illegal, or even
considered a form of espionage.

We therefore strongly urge you to consult with lawyers *prior* to running
ooniprobe. You can also reach out to us with specific inquiries at
**legal@ooni.nu**. Please note though that we are *not* lawyers, but we might be
able to seek legal advice for you or to put you in touch with lawyers who could
address your questions and/or concerns.

Some relevant resources include:

* [Tor Legal FAQ](https://www.eff.org/torchallenge/faq.html)

* [EFF Know Your Rights](https://www.eff.org/issues/know-your-rights)

**Note:** The use of OONI is at your *own risk* in accordance to OONI's software
[license](https://github.com/TheTorProject/ooni- probe/blob/master/LICENSE) and
neither the OONI project nor its parent organization, the Tor Project, can be
held liable.

**Installing ooniprobe**

As with any other software, the usage of ooniprobe can leave traces. As such,
anybody with physical or remote access to your computer might be able to see
that you have downloaded, installed or run OONI.

The installation of [Tor](https://www.torproject.org/) software, which is
designed for online anonymity, is a *prerequisite* for using OONI as all
measurements are by default sent to OONI over Tor. Furthermore, one of the
recommended tests that users run through the `oonideckgen` command line (web
connectivity test) is designed to compare HTTP requests over the network of the
user and over the Tor network. Similarly, OONI's Psiphon, Lantern and OpenVPN
tests require the installation of circumvention software. 

We therefore encourage you to consult with a lawyer on the legality of anonymity
software (such as Tor, a VPN or a proxy) *prior* to installing ooniprobe.

To remove traces of software usage, you can re-install your operating system or
wipe your computer and remove everything (operating system, programs and files)
from your hard drive.

**Running ooniprobe**

Third parties (such as your government, ISP and/or employer) monitoring your
internet activity will be able to see all web traffic generated by OONI,
including your IP address, and might be able to link it to you personally.

Many countries employ sophisticated surveillance measures that allow governments
to track individuals' online activities – even if they are using a VPN or a
proxy server to protect their privacy. In such countries, governments might be
able to identify you as a OONI user regardless of what measures you take to
protect your online privacy.

OONI's **[HTTP-invalid-request-line](https://github.com/TheTorProject/ooni-
spec/blob/master/test-specs/ts-007-http-invalid-request-line.md)** test (which
is included in oonideckgen) probably presents the *highest risk* as its use
*might* trigger the suspicion of your ISP (and possibly, of your government),
the operators of network components affected by out-of-spec messages might view
them as attacks and this could potentially lead to prosecution under **computer
misuse laws** (or other laws).

**Testing URLs for censorship**

When running either oonideckgen (OONI's software package) or OONI's **web
connectivity** test, you will connect to and download data from various websites
which are included in the following two lists:

* **Country-specific test list:**
  https://github.com/citizenlab/test-lists/tree/master/lists
  (search for your country's test list based on its country code)

* **Global test list:**
  https://github.com/citizenlab/test-lists/blob/master/lists/global.csv
  (including a list of globally accessed websites)

Many websites included in the above lists will likely be controversial and can
include pornography or hate speech, which might be illegal to access in your
country. We therefore recommend that you examine carefully whether you are
willing to take the risk of accessing and downloading data from such websites
through OONI tests, especially if this could potentially lead to various forms
of retribution.

If you are uncertain of the potential implications of connecting to and
downloading data from the websites listed in the above lists, you can pass your
*own* test list with the ooniprobe `-f` command line option.

**Publication of measurements**

The public (including third parties who view the usage of OONI as illegal or
"suspicious") will be able to see the information collected by OONI once it's
published through:

* [OONI Explorer](https://explorer.ooni.torproject.org/world/)

* [OONI's list of measurements](https://measurements.ooni.torproject.org/)

Unless users **[opt-out](https://github.com/TheTorProject/ooni-spec/blob/master
/informed-consent/data-policy.md#opt-out)**, all measurements that are generated
through OONI tests are by default sent to OONI's measurement collector and
automatically published through the above resources.

Published data will include your approximate location, the network (ASN) you are
connecting from, and when you ran ooniprobe. Other identifying information, such
as your IP address, is *not* deliberately collected, but might be included in
HTTP headers or other metadata. The full page content downloaded by OONI could
potentially include further information if, for example, a website includes
tracking codes or custom content based on your network location. Such
information could potentially aid third parties in detecting you as an ooniprobe
user.

## Choices

We provide you with choices in regards to which tests to run, which data
you would like to be collected and whether you would like to send your
measurements to our collector for publication or not, as outlined below.

**Tests**

You can *opt-out* from running all of the tests included in `oonideckgen` by
specifying the test(s) that you want to run and by running it/them manually. You
can view how to run each OONI test through the ooniprobe `-s` command line
option.

You can run each test included in `oonideckgen` separately through the following:

* **Web connectivity test:** `ooniprobe blocking/web_connectivity`

* **HTTP header field manipulation test:** `ooniprobe
    manipulation/http_header_field_manipulation`

* **HTTP invalid request line test:** `ooniprobe
    manipulation/http_invalid_request_line`

**Data collection and publication**

OONI software users can *opt-out* from sending OONI's measurement collector
specific types of data by [editing the ooniprobe
configuration](https://github.com/TheTorProject/ooni-probe#configuring-
ooniprobe) file inside of `~/.ooni/ooniprobe.conf`. Through this file, users
can opt-out from sending OONI the following types of information:

* Country code

* Autonomous System Number (ASN)

By default, OONI does *not* collect users' IP addresses, but users can choose to
*opt-in* (to provide more accurate information) through the above configuration
file.

Users can also choose to *opt-out* from sending OONI's measurement collector any
data at all, by running ooniprobe with the `-n` command line option. This option
is quite often chosen by users who prefer to *not* have their measurements
published, due to potential risks that could emerge as a result of such
publication.

Learn more about how we handle data through our Data Policy.

## Consent

My consent means the following:

I understand the requirements and the risks of running ooniprobe.

I understand that, unless I opt-out (as explained in the previous section), the
results of the tests that I run will by default be sent to the OONI project and
published by it.

PRESS q to leave this page
