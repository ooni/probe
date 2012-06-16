from zope.interface import implements, Interface, Attribute

class ITest(Interface):
    """
    This interface represents an OONI test. It fires a deferred on completion.
    """

    shortName = Attribute("""A short user facing description for this test""")
    description = Attribute("""A string containing a longer description for the test""")

    requirements = Attribute("""What is required to run this this test, for example raw socket access or UDP or TCP""")

    #deferred = Attribute("""This will be fired on test completion""")
    #node = Attribute("""This represents the node that will run the test""")
    options = Attribute("""These are the arguments to be passed to the test for it's execution""")

    blocking = Attribute("""True or False, stating if the test should be run in a thread or not.""")

    def startTest(asset):
        """
        Launches the Test with the specified arguments on a node.
        """

