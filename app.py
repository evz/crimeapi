import os
from datetime import datetime, timedelta
import pymongo
import json
from urlparse import parse_qs, urlparse
from bson import json_util

from flask import Flask, request, make_response
from raven.contrib.flask import Sentry

app = Flask(__name__)

app.url_map.strict_slashes = False

app.config['SENTRY_DSN'] = 'https://0b2a28d91b324689b12ca36f747af10e:40bf5ac282da4ecfbc4b123d147e0749@app.getsentry.com/8349'
sentry = Sentry(app)

c = pymongo.MongoClient()
db = c['chicago']
db.authenticate(os.environ['CHICAGO_MONGO_USER'], os.environ['CHICAGO_MONGO_PW'])
crime_coll = db['crime']

OK_FIELDS = [
    'year', 
    'domestic', 
    'case_number', 
    'id', 
    'primary_type', 
    'district', 
    'arrest', 
    'location', 
    'community_area', 
    'description', 
    'beat', 
    'date', 
    'ward', 
    'iucr', 
    'location_description', 
    'updated_on', 
    'fbi_code', 
    'block'
]

OK_FILTERS = [
    'lt',
    'lte',
    'gt',
    'gte',
    'near',
    'geoWithin',
    'geoIntersects',
    'in',
    'all',
    'ne',
    'nin',
    None,
]

# expects GeoJSON object as a string
# client will need to use JSON.stringify() or similar

@app.route('/api/crime/', methods=['GET'])
def crime_list():
    get = request.args.copy()
    callback = get.get('callback', None)
    maxDistance = get.get('maxDistance', 1000)
    limit = get.get('limit', 2000)
    if limit > 1000:
        limit = 1000
    if not callback:
        resp_packet = {
            'status': 'Bad Request', 
            'message': 'You must provide the name of a callback'
        }
        resp = make_response(json.dumps(resp_packet), 401)
    else:
        del get['callback']
        try:
            del get['_']
            del get['maxDistance']
        except KeyError:
            pass
        query = {}
        resp = None
        for field,value in get.items():
            filt = None
            geom = None
            try:
                field, filt = field.split('__')
            except ValueError:
                pass
            if field not in OK_FIELDS:
                resp = {
                    "status": "Bad Request", 
                    "message": "Unrecognized field: '%s'" % field,
                    "code": 400,
                }
            else:
                if field in ['date', 'updated_on']:
                    try:
                        value = datetime.fromtimestamp(float(value))
                    except TypeError:
                        resp = {
                            'status': 'Bad Request', 
                            'message': 'Date time queries expect a valid timestamp',
                            'code': 400
                        }
                if filt not in OK_FILTERS:
                    resp = {
                        'status': 'Bad Request',
                        'message': "Unrecognized query operator: '%s'" % filt,
                        'code': 400,
                    }
                elif field == 'location':
                    query[field] = {'$%s' % filt: {'$geometry': json.loads(value)}}
                    if filt == 'near':
                        query[field]['$%s' % filt]['$maxDistance'] = maxDistance
                elif filt:
                    if query.has_key(field):
                        update = {'$%s' % filt: value}
                        query[field].update(**update)
                    else:
                        query[field] = {'$%s' % filt:value}
                else:
                    query[field] = value
        if not query.has_key('date'):
            query['date'] = {'$gte': datetime.now() - timedelta(days=14)}
        if not resp:
            results = list(crime_coll.find(query).hint([('date', -1)]).limit(limit))
            resp = {
                'status': 'ok', 
                'results': results,
                'code': 200,
                'meta': {
                    'total_results': len(results),
                    'query': query,
                }
            }
        if resp['code'] == 200:
            out = make_response('%s(%s)' % (callback, json_util.dumps(resp)), resp['code'])
        else:
            sentry.captureMessage(resp)
            out = make_response(json.dumps(resp), resp['code'])
        return out

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 7777))
    app.run(host='0.0.0.0', port=port, debug=True)
