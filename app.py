import os
from datetime import datetime, timedelta
import pymongo
import json
from urlparse import parse_qs, urlparse
from bson import json_util, code
import xlwt
from cStringIO import StringIO
from itertools import groupby
from operator import itemgetter

from flask import Flask, request, make_response
from raven.contrib.flask import Sentry

app = Flask(__name__)

app.url_map.strict_slashes = False

env = os.environ.get('PROJECTENV')

DEBUG = False

if env == 'local':
    c = pymongo.MongoClient(host=os.environ['CRIME_MONGO'])
    DEBUG = True
else:
    c = pymongo.MongoClient()
    app.config['SENTRY_DSN'] = os.environ['SENTRY_URL']
    sentry = Sentry(app)
db = c['chicago']
db.authenticate(os.environ['CHICAGO_MONGO_USER'], os.environ['CHICAGO_MONGO_PW'])
crime_coll = db['crime']
iucr_coll = db['iucr']

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
    'block',
    'type',
    'time',
]

OK_FILTERS = [
    'lt',
    'lte',
    'gt',
    'gte',
    'near',
    'geoWithin',
    'in',
    'ne',
    'nin',
    None,
]

WORKSHEET_COLUMNS = [
    'date',
    'primary_type',
    'description',
    'location_description', 
    'iucr',
    'case_number',
    'block',
    'ward',
    'community_area',
    'beat',
    'district',
    'time_of_day'
]

@app.route('/api/report/', methods=['GET'])
def crime_report():
    query = urlparse(request.url).query.replace('query=', '')
    query = json_util.loads(query)
    results = list(crime_coll.find(query).hint([('date', -1)]))
    book = xlwt.Workbook()
    types = ', '.join(query['type']['$in'])
    from_date = query['date']['$gte'].strftime('%m/%d/%Y')
    to_date = query['date']['$lte'].strftime('%m/%d/%Y')
    sheet_title = 'Between %s and %s' % (from_date, to_date)
    sheet = book.add_sheet('Crime')
    for i,col_name in enumerate(WORKSHEET_COLUMNS):
        if col_name != '_id':
            sheet.write(0, i, ' '.join(col_name.split('_')).title())
    for i, result in enumerate(results):
        i += 1
        del result['_id']
        for j, key in enumerate(WORKSHEET_COLUMNS):
            try:
                value = result[key]
            except KeyError:
                value = ''
            if type(value) == datetime:
                value = result[key].strftime('%Y-%m-%d')
            if key == 'time_of_day':
                value = result['date'].strftime('%H:%M')
            sheet.write(i, j, value)
    out = StringIO()
    book.save(out)
    resp = make_response(out.getvalue())
    resp.headers['Content-Type'] = 'application/vnd.ms-excel'
    resp.headers['Content-Disposition'] = 'attachment; filename=Crime.xls'
    resp.set_cookie('fileDownload', value="true")
    return resp

# expects GeoJSON object as a string
# client will need to use JSON.stringify() or similar

@app.route('/api/crime/', methods=['GET'])
def crime_list():
    get = request.args.copy()
    callback = get.get('callback', None)
    maxDistance = get.get('maxDistance', 1000)
    limit = int(get.get('limit', 2000))
    resp_format = get.get('format', 'jsonp')
    if limit > 2000:
        limit = 2000
    if not callback:
        resp = {
            'status': 'Bad Request', 
            'message': 'You must provide the name of a callback',
            'code': 400
        }
    else:
        del get['callback']
        try:
            del get['_']
        except KeyError:
            pass
        try:
            del get['maxDistance']
        except KeyError:
            pass
        try:
            del get['limit']
        except KeyError:
            pass
        try:
            del get['format']
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
                elif field in ['fbi_code', 'iucr', 'type']:
                    query[field] = {'$in': value.split(',')}
                elif field == 'time':
                    try:
                        time_range = sorted(list(set([int(v) for v in value.split(',')])))
                        times = time_range[0], time_range[-1]
                        query['$where'] = code.Code('this.date.getHours() > %s && this.date.getHours() < %s' % times)
                    except ValueError:
                        # Someone unchecked all the boxes
                        pass
                elif filt:
                    if query.has_key(field):
                        update = {'$%s' % filt: value}
                        query[field].update(**update)
                    else:
                        query[field] = {'$%s' % filt: value}
                else:
                    query[field] = value
        if not query.has_key('date'):
            query['date'] = {'$gte': datetime.now() - timedelta(days=14)}
        if not query.has_key('type'):
            query['type'] = {'$in': ['violent', 'property', 'quality']}
        if not resp:
            results = list(crime_coll.find(query).hint([('date', -1)]).limit(limit))
            results = sorted(results, key=itemgetter('type'))
            totals_by_type = {}
            totals_by_date = {}
            for k,g in groupby(results, key=itemgetter('type')):
                totals_by_type[k] = len(list(g))
            results = sorted(results, key=itemgetter('date'))
            for k,g in groupby(results, key=itemgetter('date')):
                key = k.strftime('%Y-%m-%d')
                count = len(list(g))
                stored_count = totals_by_date.get(key, 0)
                totals_by_date[key] = stored_count + count
            resp = {
                'status': 'ok', 
                'results': results,
                'code': 200,
                'meta': {
                    'total_results': len(results),
                    'query': query,
                    'totals_by_type': totals_by_type,
                    'totals_by_date': totals_by_date,
                }
            }
        if resp['code'] == 200:
            if resp_format == 'jsonp':
                out = make_response('%s(%s)' % (callback, json_util.dumps(resp)), resp['code'])
            else:
                out = make_response(json_util.dumps(resp), resp['code'])
        else:
            if not DEBUG:
                sentry.captureMessage(resp)
            out = make_response(json.dumps(resp), resp['code'])
        return out

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 7777))
    app.run(host='0.0.0.0', port=port, debug=True)
