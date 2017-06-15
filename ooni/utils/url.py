import re

# from citizenlab/test-lists/blob/master/scripts/lint-lists.py#L10
VALID_URL = re.compile(
        r'^(?:http)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
r'(?:/?|[/?]\S+)$', re.IGNORECASE)

def validateURL(url):
    return VALID_URL.match(url)
