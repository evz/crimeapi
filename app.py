import os
import datetime
import pymongo
import json
from urlparse import parse_qs, urlparse

from flask import Flask, request

app = Flask(__name__)

app.url_map.strict_slashes = False

c = pymongo.MongoClient()
db = c['chicago']

@app.route('/crime/list/', methods=['GET'])
def crime_list():
    limit = 100
    get = request.args
    # expects GeoJSON object as a string
    # client will need to use JSON.stringify() or similar
    print get.get('near')
    callback = get.get('callback', None)
    return '%s(%s)' % (callback, json.dumps({'key':'value'}))

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 6666))
    app.run(host='0.0.0.0', port=port)
