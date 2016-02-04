Writing Test Helpers
========

OONI test helpers are used by OONI nettests to perform their measurements. They can be used either to establish a ground truth or to exchange information with the probe to determine if some form of network manipulation is happening in the network path between the probe and the backend.

Writing a Censorship Directionality Test Helper
--------------------------

Our goal is to write an OONI test helper that helps an ooni-probe client determine the directionality of keyword censorship it has detected. To do this our helper will receive "encoded" data from an OONI-probe client, decode that data into a text string, and send the OONI-probe client a confirmation packet and a second packet containing the decoded string.

The ooni-backend code-base has many concise examples of test-helpers that you can build off to create your own. For this tutorial I used the `TCP echo test-helper <https://github.com/TheTorProject/ooni-backend/blob/479a1bb154037b834292ccc4b3d593d1472b44de/oonib/testhelpers/tcp_helpers.py#L9-L18>`_ as my guide.

Following this tutorial requires basic knowledge of event-driven programming (specifically 'Twisted'). You will be more than ready to build and implement a test-helper after reading though one or two `tutorials online. <http://krondo.com/?page_id=1327>`_

Creating the test helper
--------------

ooni-backend keeps all the test-helpers in the `oonib/testhelpers directory <https://github.com/TheTorProject/ooni-backend/tree/master/oonib/testhelpers>`_ Each individual test helper is a twisted service. Most of the current test-helpers consists of a twisted Factory and a twisted Protocol defined in the test helpers directory and a `stock Twisted Server <https://twistedmatrix.com/documents/current/api/twisted.application.internet.html>`_ that is defined in the backend code. We will follow this model in the tutorial.

Because of how simple this example test-helper is the job of our test-helper factory is merely to deploy a single instance of our protocol each time it's buildProtocol method is called. Because we have our factory inhered from the base `Factory object <https://twistedmatrix.com/trac/browser/tags/releases/twisted-15.5.0/twisted/internet/protocol.py#L27>`_ we merely have to define its ``protocol`` property to point to our protocol.::

    class TCPDirectionalityTestHelper(Factory):
        """
        A test helper for checking for directionality of censorship
        """
        protocol = TCPDirectionalityTestProtocol


The protocol for this helper needs to do two things. First, upon receiving encoded data it needs to send the ooni-probe client back confirmation that the data has been received. Second, it needs to send the decoded data back to the OONI-probe client. Because we are extending the `Protocol object <https://twistedmatrix.com/trac/browser/tags/releases/twisted-15.5.0/twisted/internet/protocol.py#L512>`_ we can rewrite its ``dataReceived`` method which is called and passed data whenever it is received.::


    class TCPDirectionalityTestProtocol(Protocol):
        """Takes encoded packet data, decodes it, and then sends it back.

        This protocol sends two packets in response to an encoded packet.
        It first sends a confirmation packet, and then follows with a packet
        containing the decoded data requested from the test.
        """
        def dataReceived(self, data):
            # send back receipt of the packet
            self.transport.write(data)
            # send back the decoded term to test against.
            original_string = data.decode("rot13").decode("unicode-escape").encode("utf-8")
            self.transport.write(original_string)


In order to make this test-helper slightly more flexible we will be allowing the backend to determine the encoding within their config file. To this end we will have to retrieve the encoding from the config file.::


        def dataReceived(self, data):
            # send back receipt of the packet
            self.transport.write(data)

            # Get the encoding from the config or fallback to rot13
            if config.helpers['tcp-directionality'].encoding:
                tcp_dir_encoding = config.helpers['tcp-directionality'].encoding
            else:
                tcp_dir_encoding = "rot13"

            # send back the decoded term to test against.
            original_string = data.decode("rot13").decode("unicode-escape").encode("utf-8")
            self.transport.write(original_string)


With this added we have completed the base of simple test-helper and now just have to integrate it into the rest of the backend.


Adding the helper to the config file
------

ooni-backend uses a config file located at `/etc/oonibackend.conf <https://github.com/TheTorProject/ooni-backend/blob/master/oonib.conf.example>`_. This file contains a `section where each test-helper can be configured. <https://github.com/TheTorProject/ooni-backend/blob/479a1bb154037b834292ccc4b3d593d1472b44de/oonib.conf.example#L33-L65>`_.

The test-helper will need to be given a unique identifier so that it can be called from the config file. In this example we use ``tcp-directionality`` as our identifier.

For a helper to be used in the ooni-backend it needs to be given an identifier so that it can be called from the config file::

      tcp-directionality:
        encoding: rot13
        port: 57009

Adding the helper to the backend
------

For a helper to be integrated into the ooni-backend it needs to be added to the initialization scripts contained within `oonibackend.py <https://github.com/TheTorProject/ooni-backend/blob/master/oonib/oonibackend.py>`_.

The OONI test-helper system is a collection of `Twisted services <https://twistedmatrix.com/documents/current/core/howto/application.html>`_. For our test-helper we will need to define a service that will run our test-helper factory.::

        # Create the service that will run our test-helpers factory.
        tcp_directionality_helper = internet.TCPServer(int(port),
                                             tcp_helpers.TCPDirectionalityTestHelper())

**NOTE:** In this example I have placed the original service in the existing tcp_helpers file. If you created your own file for your test-helper you will have to make sure that you import that file at the top of `oonibackend.py <https://github.com/TheTorProject/ooni-backend/blob/master/oonib/oonibackend.py>`_.

OONI uses a `Multi Service <https://twistedmatrix.com/documents/current/api/twisted.application.service.MultiService.html>`_ which allows them to combine all the OONI test-helpers and the report-collector into a singular service for easier management. The next step for creating our test-helper is to add it to the ooni-backend `multiService <https://github.com/TheTorProject/ooni-backend/blob/479a1bb154037b834292ccc4b3d593d1472b44de/oonib/oonibackend.py#L33>`_::

        # Add the helper as a child of the backends multi-service test-helper
        multiService.addService(tcp_directionality_helper)

Finally, we need to start our service.::

        # Start the test-helpers service
        tcp_directionality_helper.startService()

In order for our test-helper to be managed using the backend config file we will need to modify this code to check the config file for a test-helper that uses the identifier we selected earlier. For the directionality helper we check to see if our test-helper had its port specified in the config file to determine if it should be run. I also added a default encoding in case

This snippet contains the final code that would be inserted into `oonibackend.py <https://github.com/TheTorProject/ooni-backend/blob/master/oonib/oonibackend.py>`_.::

    # Check to see if our test-helper was defined in the config
    if config.helpers['tcp-directionality'].port:
        print "Starting TCP directionality helper on %s" % config.helpers['tcp-directionality'].port

        # Check for encoding in our config file and set default if missing
        if config.helpers['tcp-directionality'].encoding:
            tcp_dir_encoding = config.helpers['tcp-directionality'].encoding
        else:
            tcp_dir_encoding = "rot13"
        # Get & set the port and encoding from our config file
        tcp_directionality_helper = internet.TCPServer(int(config.helpers['tcp-directionality'].port),
                                             tcp_helpers.TCPDirectionalityTestHelper(tcp_dir_encoding))

        # Add the helper as a child of the backends multi-service test-helper
        multiService.addService(tcp_directionality_helper)

        # Start the test-helpers service
        tcp_directionality_helper.startService()


Requiring the helper in a test
-------------

If you are creating tests that rely on custom test-helpers you will want to make sure that you do not get inaccurate results because your test-helper being missing in the ooni-backend you are testing against. You can specify required test-helpers within a ooni-probe test by setting its ``requiredTestHelpers`` property. In this example we have made our test helper require the tcp-directionality test that we created above.::

    class MyDirectionalityTest(nettest.NetTestCase):
    """ An example test."""

        requiredTestHelpers = {'backend': 'tcp-directionality'}
        ...
