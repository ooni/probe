from ooni import __resources_version__ as resources_version

__version__ = "0.2.0"

ooni_resources_url = ("https://github.com/TheTorProject/ooni-probe/releases"
                      "/download/v{}/"
                      "ooni-resources.tar.gz").format(resources_version)
