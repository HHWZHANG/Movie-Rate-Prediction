from urllib.parse import urlparse, urljoin
from flask import request, url_for


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc



def is_number(n):
    try:
        float(n)
        return True
    except:
        return False



def nullable_sort(a,b):
    if a is None:
        return 1
    if b is None:
        return -1
    if a < b:
        return -1
    if a > b:
        return 1
    return 0


