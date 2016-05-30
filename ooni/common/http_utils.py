import re
import codecs
from base64 import b64encode

META_CHARSET_REGEXP = re.compile('<meta(?!\s*(?:name|value)\s*=)[^>]*?charset\s*=[\s"\']*([^\s"\'/>!;]+)')

def representBody(body):
    if not body:
        return body
    # XXX perhaps add support for decoding gzip in the future.
    body = body.replace('\0', '')
    decoded = False
    charsets = ['ascii', 'utf-8']

    # If we are able to detect the charset of body from the meta tag
    # try to decode using that one first
    charset = META_CHARSET_REGEXP.search(body, re.IGNORECASE)
    if charset:
        try:
            encoding = charset.group(1).lower()
            codecs.lookup(encoding)
            charsets.insert(0, encoding)
        except (LookupError, IndexError):
            # Skip invalid codecs and partial regexp match
            pass

    for encoding in charsets:
        try:
            body = unicode(body, encoding)
            decoded = True
            break
        except UnicodeDecodeError:
            pass
    if not decoded:
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
