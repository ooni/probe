import os
import random

from twisted.application import service, internet
from twisted.web import static, server

from ooni.settings import config
from ooni.api.spec import oonidApplication
from ooni.director import Director
from ooni.reporter import YAMLReporter, OONIBReporter

def getOonid():
    director = Director()
    director.start()
    oonidApplication.director = director
    return internet.TCPServer(int(config.advanced.oonid_api_port), oonidApplication)

application = service.Application("ooniprobe")
service = getOonid()
service.setServiceParent(application)
