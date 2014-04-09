import requests
import os
from urlparse import urlparse

def dl_write(url):
    path = urlparse(url)
    name = path.path.replace('/', '-')
    full_path = os.path.join('/tmp', name)
    try:
        f = open('/tmp/' + name)
    except IOError:
        tile = requests.get(url)
        outp = open('/tmp/' + name, 'wb')
        outp.write(tile.content)
    return full_path

def dl_write_all(links):
    paths = []
    for link in links:
        paths.append(dl_write(link))
    return paths

def hex_to_rgb(value):
    value = value.lstrip('#')
    lv = len(value)
    return tuple(int(value[i:i+lv/3], 16) for i in range(0, lv, lv/3))
