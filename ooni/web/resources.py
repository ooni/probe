import json
from twisted.web import resource
from twisted.python import usage

from ooni import errors
from ooni.nettest import NetTestLoader


class WuiResource(resource.Resource):
    isLeaf = True
    XSRF_HEADER = 'X-XSRF-TOKEN'
    # XXX set this to true when stable version
    XSRF_PROTECTION = False

    def __init__(self, director):
        self.director = director
        resource.Resource.__init__(self)

    def check_xsrf(self, request):
        if self.XSRF_PROTECTION is False:
            return True
        if request.requestHeaders.hasHeader(self.XSRF_HEADER):
            return True
        return False

    def render(self, request):
        if not self.check_xsrf(request):
            obj = {
                'error_code': 400,
                'error_message': ('Missing cross site request forgery '
                                  'header \'{}\''.format(self.XSRF_HEADER))
            }
            request.setResponseCode(403)
            return self.render_json(obj, request)
        obj = resource.Resource.render(self, request)
        return self.render_json(obj, request)

    def render_json(self, obj, request):
        json_string = json.dumps(obj) + "\n"
        request.setHeader('Content-Type', 'application/json')
        request.setHeader('Content-Length', len(json_string))
        return json_string


class DecksGenerate(WuiResource):
    def render_GET(self, request):
        return {"generate": "deck"}


class DecksStart(WuiResource):
    def __init__(self, director, deck_name):
        WuiResource.__init__(self, director)
        self.deck_name = deck_name

    def render_GET(self, request):
        return {"start": self.deck_name}


class DecksStop(WuiResource):
    def __init__(self, director, deck_id):
        WuiResource.__init__(self, director)
        self.deck_id = deck_id

    def render_GET(self, request):
        return {"stop": self.deck_id}


class DecksStatus(WuiResource):
    def __init__(self, director, deck_name):
        WuiResource.__init__(self, director)
        self.deck_name = deck_name

    def render_GET(self, request):
        return {"deck": self.deck_name}


class DecksList(WuiResource):
    def render_GET(self, request):
        return {"deck": "list"}


def getNetTestLoader(test_options, test_file):
    """
    Args:
        test_options: (dict) containing as keys the option names.

        test_file: (string) the path to the test_file to be run.
    Returns:
        an instance of :class:`ooni.nettest.NetTestLoader` with the specified
        test_file and the specified options.
        """
    options = []
    for k, v in test_options.items():
        options.append('--'+k)
        options.append(v)

    net_test_loader = NetTestLoader(options,
            test_file=test_file)
    return net_test_loader

class TestsStart(WuiResource):
    def __init__(self, director, test_name):
        WuiResource.__init__(self, director)
        self.test_name = test_name

    def render_POST(self, request):
        try:
            net_test = self.director.netTests[self.test_name]
        except KeyError:
            request.setResponseCode(500)
            return {
                'error_code': 500,
                'error_message': 'Could not find the specified test'
            }
        test_options = json.load(request.content)
        net_test_loader = getNetTestLoader(test_options, net_test['path'])
        try:
            net_test_loader.checkOptions()
            # XXX we actually want to generate the report_filename in a smart
            # way so that we can know where it is located and learn the results
            # of the measurement.
            report_filename = None
            self.director.startNetTest(net_test_loader, report_filename)
        except errors.MissingRequiredOption, option_name:
            request.setResponseCode(500)
            return {
                'error_code': 501,
                'error_message': ('Missing required option: '
                                  '\'{}\''.format(option_name))
            }
        except usage.UsageError:
            request.setResponseCode(500)
            return {
                'error_code': 502,
                'error_message': 'Error in parsing options'
            }
        except errors.InsufficientPrivileges:
            request.setResponseCode(500)
            return {
                'error_code': 503,
                'error_message': 'Insufficient priviledges'
            }

        return {"deck": "list"}


class TestsStop(WuiResource):
    def __init__(self, director, test_id):
        WuiResource.__init__(self, director)
        self.test_id = test_id

    def render_GET(self, request):
        return {"deck": "list"}


class TestsStatus(WuiResource):
    def __init__(self, director, test_id):
        WuiResource.__init__(self, director)
        self.test_id = test_id

    def render_GET(self, request):
        return {"deck": "list"}


class TestsList(WuiResource):
    def render_GET(self, request):
        return self.director.netTests


class Results(WuiResource):
    def render_GET(self, request):
        return {"result": "bar"}
