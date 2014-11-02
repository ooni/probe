from twisted.application import service, internet

from ooni.settings import config
from ooni.api.spec import oonidApplication
from ooni.director import Director

def getOonid():
    director = Director()
    director.start()
    oonidApplication.director = director
    return internet.TCPServer(int(config.advanced.oonid_api_port), oonidApplication)

application = service.Application("ooniprobe")
service = getOonid()
service.setServiceParent(application)
