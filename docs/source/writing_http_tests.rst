.. code:: python

  class HTTPRequest(httpt.HTTPTest):
      def test_send_headers(self):
          r = yield self.request.get("http://ooni.nu/",
                                     headers={'Foo': 'bar'})
          print r.headers
          print r.status_code

          print r.text
          print r.content
