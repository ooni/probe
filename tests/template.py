"""
    Test Template
    *************

    This is a Test template, to be used when writing your
    own OONI probe Tests.
"""
from plugoo.assets import Asset
from plugoo.tests import Test

__plugoo__ = "Test Template"
__desc__ = "This a test template to be used to build your own tests"

class TestTemplateAsset(Asset):
    """
    This is the asset that should be used by the Test. It will
    contain all the code responsible for parsing the asset file
    and should be passed on instantiation to the test.
    """
    def __init__(self, file=None):
        self = asset.__init__(self, file)


class TestTemplate(Test):
    """
    The main Test class
    """

    def experiment(self, *a, **kw):
        """
        Fill this up with the tasks that should be performed
        on the "dirty" network and should be compared with the
        control.
        """
        pass

    def control(self):
        """
        Fill this up with the control related code.
        """
        pass

def run(ooni):
    """
    This is the function that will be called by OONI
    and it is responsible for instantiating and passing
    the arguments to the Test class.
    """
    config = ooni.config

    # This the assets array to be passed to the run function of
    # the test
    assets = [TestTemplateAsset(os.path.join(config.main.assetdir, \
                                            "someasset.txt"))]

    # Instantiate the Test
    thetest = TestTemplate(ooni)
    ooni.logger.info("starting TestTemplate...")
    # Run the test with argument assets
    thetest.run(assets)
    ooni.logger.info("finished.")


