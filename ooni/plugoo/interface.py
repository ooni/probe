from zope.interface import implements, Interface, Attribute

class ITest(Interface):
    """
    This interface represents an OONI test. It fires a deferred on completion.
    """

    shortName = Attribute("""A short user facing description for this test""")
    description = Attribute("""A string containing a longer description for the test""")

    requirements = Attribute("""What is required to run this this test, for example raw socket access or UDP or TCP""")

    options = Attribute("""These are the arguments to be passed to the test for it's execution""")

    blocking = Attribute("""True or False, stating if the test should be run in a thread or not.""")

    def control(experiment_result, args):
        """
        @param experiment_result: The result returned by the experiment method.

        @param args: the keys of this dict are the names of the assets passed in
        from load_assets. The value is one item of the asset.

        Must return a dict containing what should be written to the report.
        Anything returned by control ends up inside of the YAMLOONI report.
        """

    def experiment(args):
        """
        Perform all the operations that are necessary to running a test.

        @param args: the keys of this dict are the names of the assets passed in
        from load_assets. The value is one item of the asset.

        Must return a dict containing the values to be passed to control.
        """

    def load_assets():
        """
        Load the assets that should be passed to the Test. These are the inputs
        to the OONI test.
        Must return a dict that has as keys the asset names and values the
        asset contents.
        If the test does not have any assets it should return an empty dict.
        """

    def end():
        """
        This can be called at any time to terminate the execution of all of
        these test instances.

        What this means is that no more test instances with new parameters will
        be created. A report will be written.
        """

