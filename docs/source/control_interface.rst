====================================
HTTP Control Interface Specification
====================================

The ``ooniprobe`` client provides a HTTP-based control interface. The goal of
this interface is to allow applications to interact with ooniprobe in a
standardized manner. The control interface aims to be a RESTful, stateless 
and simple protocol.

This control interface will be exposed as an HTTP service that communicates
using JSON encoded messages. The service shall be provided via the ooniprobe
daemon, ``oonid``.

While the HTTP Control Interface is **currently under development** with
a HTML/JS WebGUI client in mind, it will also be compatible with other
clients, such as Ledilopter (ooniprobe on the Raspberry Pi) and 3rd party
tools.


.. contents:: **Table of Contents**
   :depth: 2

General Notes
.............
This document is the working specification for ooniprobe HTTP Control
Interface version 0. 

All the fields defined in this specification are mandatory, unless explicitly
marked otherwise.

All successful client requests should return a 2xx status code, and should
return return a JSON encoded body if required in the specification below.
Failed (or deferred) requests will cause a 3xx, 4xx or 5xx status code on
response. All failure responses must return a JSON encoded body with the
following format::

    {
     'error_code': <some_integer_error_code>,
     'error_message': <some_string_explanation>
    }

In particular, should the client make a request to a invalid URI, the service
shall respond with ``Status-code: 404`` and the reponse body::

    {
     'error_code': 404,
     'error_message': 'Resource Not Found'
    }

If the client makes a request with invalid syntax that prevents the service
from understanding the request, the service shall return ``Status-code: 400``
and the response body::

    {
     'error_code': 400,
     'error_message': 'Invalid syntax'
    }

Error handling is the client's responsibility.

All date and time records in this specification shall be encoded according to 
`ISO 8601 <https://en.wikipedia.org/wiki/ISO_8601>`_.

Decks
.....
Testing in OONI is centered around 'decks'. A deck is defined as a collection 
of network tests and their associated inputs.

List decks
^^^^^^^^^^
To retrieve an array of all available decks:

``GET /decks``

The server shall repond with ``Status-code: 200`` and a body format::

    [{'id': 'deck-it',
       'name': 'Deck for Italy',
       'description': 'blah blah blah',
       'nettests': [ 'http_invalid_request_line',
                     'http_header_field_manipulation',
                     'dns_consistency'],
    }]

Where ``nettests`` must refer to valid test IDs. The service may return an
empty list if no tests are found.

If the service is unable to retrieve the list of decks, it shall return a
reponse with ``Status-code: 500`` and a body format::

    {
     'error_code': 500,
     'error_message': 'Internal Server Error - Could not find directory "decks"'
    }

Generate decks
^^^^^^^^^^^^^^
Decks can either be generated for a specific country, or you can let
oonideckgen try to automatically detect the country.

``POST /decks``

Request format::

    {
      'country': 'CN' // optional, oonideckgen will autodetect otherwise
    }

On success, the service shall respond with ``status code 200`` and with the
following body format::

    {
      'deck_id': 'deck-cn'
    }

Deck IDs are not guaranteed to be unique - if the exact same deck has been
created through an earlier request, the service shall reply with the old
deck ID.

If the operation fails the service shall respond with the appropriate status
code and message.

In particular, if the client makes invalid deck generation request, the
service shall reply with ``Status-Code: 400`` and body message formatted::

    {
     'error_code': 400,
     'error_message': 'Bad Request - "xy" is not a valid ISO country code'
    }

If the server is unable to generate a deck due to an internal error, it shall
respond with ``Status-Code: 500`` and a body message formatted::

    {
     'error_code': 500,
     'error_message': 'Internal Error - oonideckgen: couldn't fetch "http://someurl.com"'
    }

Start deck
^^^^^^^^^^
``POST /decks/<deck_id>/start``

To run a deck, the above POST request is sent where ``deck_id`` must be a
valid deck ID. 

Request format::

    {
     'collector': true,                    // optional, defaults to true
     'bouncer': 'http://someaddress.onion' // optional, defaults to httpo://XXX
    }

On success, the server shall respond with ``Status-Code: 200`` and with the
following body format::

    {
     'current_nettest': 'dns_consistency',
     'time_started': '2014-03-12T13:37:27+00:00'
    }

If the service is unable to start the test, it shall respond with the 
appropriate status code and message.

In particular, if the client attempts to run multiple decks simoultensouly,
the service shall respond with ``Status-Code: 503`` and the body::

    {
     'error_code': 503,
     'error_message': 'Unable to handle request - another deck is already running'
    }

If the service is unable to start the deck due to an interal error (for example, corrupted input files) it shall respond with ``Status-Code: 500`` and
the body::

    {
     'error_code': 500,
     'error_message': 'Unable to handle request - oonid: unable to find input file "DNE.txt"'
    }

Stop deck
^^^^^^^^^
``GET /decks/<deck_id>/stop``

To stop a deck, the above GET request is sent where ``deck_id`` must be a
valid deck ID.

On success, the service shall respond with ``Status-Code: 204 - No Content``.

If the requested deck is not running, the service shall repond with ``Status-Code: 400``
and the body formatted::

    {
     'error_code': 400,
     'error_message': 'Invalid Request - Deck is not running'
    }

Should the server be unable to stop the test, it shall repond with
``Status-Code: 500`` and display a reason in the body in the following format::

    {
     'error_code': 500,
     'error_message': 'Unable to handle request - out of RAM'
    }

Deck progress
^^^^^^^^^^^^^
``GET /decks/<deck_id>``

Returns the deck progress if the deck is running, or the deck results in 
JSON format if the deck is complete.

If the deck progress is successfully found, the service shall respond with
``Status-code: 200`` and a response body formatted as follows::

    {
     'status': 'running',
     'percentage': 32,
     'current_nettest': 'http_headers',
     'results': null
    }

Another possible response body::

    {
     'status': 'complete',
     'percentage': 100,
     'current_nettest': null,
     'results': '<result_id>' 
    }

The ``status`` field may be one of: ``stopped``, ``running`` or ``complete``.
``results`` must be a valid result ID or ``null`` if the test is not yet 
finished.

Otherwise, if the deck exists but the progress request fails, the service
shall respond with ``Status-code: 500`` and an explanation in the following
format::

    {
     'error_code': 500,
     'error_message': 'Internal Server Error - could not find deck result ID'
    }

Net Tests
.........
In OONI, a ``nettest`` represents an individual anomaly detection technique. 
To run, nettests also require an input file which specifies on which URIs the
test is to be performed.

Usually, several nettests are bundled along with their inputs in a deck, which
makes it easier for the end user to run. Nonetheless, the control interface
allows for nettests to be run individually.

List tests
^^^^^^^^^^
To retrieve an array of all available nettests:

``GET /tests``

On success, the service shall repond with ``Status-code: 200`` and a body formatted::

    [
        {'id': 'dns-consistency',
           'name': 'DNS Consistency',
           'description': 'Compares the results of two DNS lookups',
           'type': 'blocking',
           'version': '0.1',
           'arguments': {
             'urllist': 'Specify the list of URLs to be used for the test'
           }, ...
        }, ...
    ]

Where ``nettests`` must refer to valid test IDs. The field ``type`` may be
of value ``blocking`` or ``manipulation``. If no decks are found, the service
will still respond with ``Status-code: 200`` and an empty list.

If the service is unable to retrieve the list of decks, it shall return a
reponse with ``Status-code: 500`` and a body format::

    {
     'error_code': 500,
     'error_message': 'Internal Server Error - Could not find directory "decks"'
    }

Starting a Test
^^^^^^^^^^^^^^^
To run a given test, the client must send the following request:
``POST /tests/<test_id>/start``

With the request body::

    {
     'urllist':
      ['http://google.com/', 'http://torproject.org']
    }

The server shall respond with ``status code 200`` with the body::

    {
     'time_started': '2014-03-12T13:37:27+00:00',
     'percentage': 55,
     'current_input': 'http://google.com',
     'arguments': [<list of supplied arguments>]
    }

Else, the reponse shall be a error status code and an explanation. In
particular, the service shall respond with ``Status-Code: 400`` if the user
provides an invalid argument or ``Status-Code: 500`` if the server is unable
to start the test due to an internal reason.

Stopping a Test
^^^^^^^^^^^^^^^
To terminate a given test, the client sends the following request:
``GET /tests/<test_id>/stop``

The server shall respond with status code 204 - no content - or with an error
message if it is unable to stop the test.

If the requested nettest is not running, the service shall repond with ``Status-Code: 400``
and the body formatted::

    {
     'error_code': 400,
     'error_message': 'Invalid Request - nettest is not running'
    }

Should the server be unable to stop the test, it shall repond with
``Status-Code: 503`` and display a reason in the body in the following format::

    {
     'error_code': 503,
     'error_message': 'Unable to handle request - out of RAM'
    }

Test progress
^^^^^^^^^^^^^
``GET /tests/<test_id>``

The service will respond with ``Status-Code 200`` and a body formatted::

    {
     'status': 'running',
     'time_started': '2014-03-12T13:37:27+00:00',
     'percentage': 55,
     'current_input': 'http://google.com',
     'arguments': [<list of supplied arguments>],
     'results': <result_id>
    }

The ``status`` field may be one of: ``stopped``, ``running`` or ``complete``.
``results`` must be a valid result ID or ``null`` if the test is not yet 
finished.

Should the service fail to determine the progress of a nettest, it shall return
``Status-code: 503`` along with a suitable error message.

Results
.......
``GET /results``

Returns a list of all stored results of previous runs.

The service will respond with ``Status-code: 200`` and results formatted::

    [
     {'id': '<result_id>',
      'type': 'deck',
      'deck': '<deck_id>',
      'time_started': '2014-03-12T13:37:27+00:00',
      'time_finished': '2014-03-12T13:37:27+00:00',
      'collector': true,
      'collector-address': 'httpo://nkvphnp3p6agi5qq.onion',
      'nettests': ['http_headers', 'http_requests', ...]
     }, ...
    ]

Where ``type`` shall be either ``deck`` or ``nettest``. If the result is of
type ``deck``, then the fields ``deck_id`` and ``nettests`` are mandatory.
Likewise, if the result is of type ``nettest`` the field ``test_id`` shall
be mandatory.

To get the results of the individual nettests (that are part of a deck)
in JSON format:

``GET /results/<result_id>/nettest/<nettest_id>``

Please be warned that this will return the raw output of the test, which may be
in excess of several tens of megabytes.

The server should return ``Status-Code 500`` and an explanation should it
fail to collect the results.

Deleting Results
^^^^^^^^^^^^^^^^

To delete a particular result:

``GET /results/<result_id>/delete``

After deletion, the service shall reply with ``Status-code: 204`` - no content.
The server shall reply with ``Status-code: 503`` should deletion fail.

Resources
.........
To update ooniprobe's geoIP databases or input files, the client may send 
the following request:

``POST /resources/update``

With the body formatted as::

    {
     'update_geoIP': true,
     'update_inputs': false
    }

The server shall reply with the ``204`` status code or if the update fails,
``503`` status code.

TODO
....
Open questions include:

* Authentication. Users probably don't want anyone who can access port 80
  on their machines to control ooniprobe.

* Protocol signaling. Ideally we want some way to make clients aware of
  different protocol versions.
