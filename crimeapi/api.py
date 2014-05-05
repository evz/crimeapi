import os
from datetime import datetime, timedelta
import pymongo
import json
from urlparse import parse_qs, urlparse
from urllib import unquote
from bson import json_util, code
import xlwt
from cStringIO import StringIO
from itertools import groupby
from operator import itemgetter
from lookups import OK_FIELDS, OK_FILTERS, WORKSHEET_COLUMNS, TYPE_GROUPS
from pdfer.core import pdfer

from flask import Blueprint, request, make_response
from raven.contrib.flask import Sentry

api = Blueprint('api', __name__)

@api.route('/api/report/', methods=['GET'])
def crime_report():
    query = urlparse(request.url).query.replace('query=', '')
    query = json_util.loads(unquote(query))
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
    now = datetime.now().isoformat().split('.')[0]
    resp.headers['Content-Disposition'] = 'attachment; filename=Crime_%s.xls' % now
    return resp

# expects GeoJSON object as a string
# client will need to use JSON.stringify() or similar

@api.route('/api/print/', methods=['GET'])
def print_page():
    query = urlparse(request.url).query.replace('query=', '')
    params = json_util.loads(unquote(query))
    results = list(crime_coll.find(params['query']).hint([('date', -1)]))
    results = sorted(results, key=itemgetter('type'))
    point_overlays = []
    print_data = {
        'dimensions': params['dimensions'],
        'zoom': params['zoom'],
        'center': params['center'],
    }
    colors = {
        'violent': '#7b3294',
        'property': '#ca0020',
        'quality': '#008837',
    }
    for k,g in groupby(results, key=itemgetter('type')):
        points = [r['location']['coordinates'] for r in list(g)]
        point_overlays.append({'color': colors[k], 'points': points})
    print_data['overlays'] = {'point_overlays': point_overlays}
    print_data['overlays']['beat_overlays'] = []
    print_data['overlays']['shape_overlays'] = []
    if 'beat' in params['query'].keys():
        print_data['overlays']['beat_overlays'] = params['query']['beat']['$in']
    if 'location' in params['query'].keys():
        print_data['overlays']['shape_overlay'] = params['query']['location']['$geoWithin']['$geometry']
    path = pdfer(print_data)
    resp = make_response(open(path, 'rb').read())
    resp.headers['Content-Type'] = 'application/pdf'
    now = datetime.now().isoformat().split('.')[0]
    resp.headers['Content-Disposition'] = 'attachment; filename=Crime_%s.pdf' % now
    return resp

@api.route('/api/crime/', methods=['GET'])
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
                elif field in ['type', 'primary_type']:
                    query[field] = {'$in': value.split(',')}
                elif field in ['fbi_code', 'iucr', 'beat']:
                    vals = value.split(',')
                    vals.extend([int(v) for v in vals])
                    query[field] = {'$in': list(set(vals))}
                elif field == 'location_description':
                    groups = value.split(',')
                    vals = []
                    for group in groups:
                        vals.extend(TYPE_GROUPS[group])
                    query['location_description'] = {'$in': vals}
                elif field == 'time':
                    try:
                        time_range = sorted(list(set([int(v) for v in value.split(',')])))
                        times = time_range[0], time_range[-1]
                        query['$where'] = code.Code('this.date.getHours() >= %s && this.date.getHours() < %s' % times)
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
