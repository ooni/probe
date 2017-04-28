import re
from base64 import b64encode


def representBody(body):
    if not body:
        return body
    if isinstance(body, unicode):
        return body
    try:
        body = unicode(body, 'utf-8')
    except UnicodeDecodeError:
        body = {
            'data': b64encode(body),
            'format': 'base64'
        }
    return body

TITLE_REGEXP = re.compile("<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)

def extractTitle(body):
    m = TITLE_REGEXP.search(body, re.IGNORECASE | re.DOTALL)
    if m:
        return unicode(m.group(1), errors='ignore')
    return ''

REQUEST_HEADERS = {
    'User-Agent': ['Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, '
                   'like Gecko) Chrome/47.0.2526.106 Safari/537.36'],
    'Accept-Language': ['en-US;q=0.8,en;q=0.5'],
    'Accept': ['text/html,application/xhtml+xml,application/xml;q=0.9,'
               '*/*;q=0.8']
}
