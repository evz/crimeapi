import os
from datetime import datetime, timedelta
import json
import requests
from urlparse import parse_qs, urlparse
from urllib import unquote
import xlwt
from cStringIO import StringIO
from itertools import groupby
from operator import itemgetter
from lookups import WORKSHEET_COLUMNS, TYPE_GROUPS, COMM_AREA
#from pdfer.core import pdfer
import sqlite3
from dateutil import parser

from flask import Flask, request, make_response, g, current_app, \
        abort, send_from_directory
from functools import update_wrapper
from app_config import WOPR_URL, CRIME_SENTRY_URL, LASCAUX_URL


app = Flask(__name__)

if CRIME_SENTRY_URL:
    from raven.contrib.flask import Sentry
    app.config['SENTRY_DSN'] = os.environ['CRIME_SENTRY_URL']
    sentry = Sentry(app)

app.url_map.strict_slashes = False

DEBUG = False

DATABASE = 'iucr_codes.db'

def crossdomain(origin=None, methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True): # pragma: no cover
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, basestring):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, basestring):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers

            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)
    return decorator

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    def make_dicts(cursor, row):
        return dict((cursor.description[idx][0], value)
                    for idx, value in enumerate(row))
    db.row_factory = make_dicts
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/api/iucr-codes/')
@crossdomain(origin="*")
def iucr_codes():
    cur = get_db().cursor()
    q = 'select * from iucr'
    args = ()
    if request.args.get('fbi_code'):
        q = '%s where fbi_code = ?' % q
        args = (request.args['fbi_code'],)
    cur.execute(q, args)
    res = cur.fetchall()
    resp = make_response(json.dumps(res))
    resp.headers['Content-Type'] = 'application/json'
    return resp

@app.route('/api/iucr-to-type/')
@crossdomain(origin="*")
def iucr_to_type():
    cur = get_db().cursor()
    cur.execute('select iucr, type from iucr')
    res = cur.fetchall()
    results = {i['iucr']: i['type'] for i in res}
    cur.close()
    resp = make_response(json.dumps(results))
    resp.headers['Content-Type'] = 'application/json'
    return resp

@app.route('/api/type-to-iucr/')
@crossdomain(origin="*")
def type_to_iucr():
    cur = get_db().cursor()
    cur.execute('select * from iucr')
    res = cur.fetchall()
    cur.close()
    res = sorted(res, key=itemgetter('type'))
    results = {}
    for k, g in groupby(res, key=itemgetter('type')):
        results[k] = list(g)
    resp = make_response(json.dumps(results))
    resp.headers['Content-Type'] = 'application/json'
    return resp

@app.route('/api/group-to-location/')
@crossdomain(origin="*")
def group_to_location():
    resp = make_response(json.dumps(TYPE_GROUPS, sort_keys=False))
    resp.headers['Content-Type'] = 'application/json'
    return resp

@app.route('/api/location-to-group/')
@crossdomain(origin="*")
def location_to_group():
    results = {}
    for group,locations in TYPE_GROUPS.items():
        for location in locations:
            results[location] = group
    resp = make_response(json.dumps(results))
    resp.headers['Content-Type'] = 'application/json'
    return resp

@app.route('/api/report/', methods=['GET'])
def crime_report():
    query = urlparse(request.url).query.replace('query=', '')
    query = json.loads(unquote(query))
    results = requests.get('%s/api/detail/' % WOPR_URL, params=query)
    book = xlwt.Workbook()
    from_date = query['obs_date__ge']
    to_date = query['obs_date__le']
    sheet_title = 'Between %s and %s' % (from_date, to_date)
    sheet = book.add_sheet('Crime')
    if results.status_code == 200:
        results = results.json()['objects']
        for i,col_name in enumerate(WORKSHEET_COLUMNS):
            if col_name != '_id':
                sheet.write(0, i, ' '.join(col_name.split('_')).title())
        for i, result in enumerate(results):
            i += 1
            for j, key in enumerate(WORKSHEET_COLUMNS):
                try:
                    value = result[key]
                except KeyError:
                    value = ''
                if key == 'time_of_day':
                    value = parser.parse(result['orig_date']).strftime('%H:%M')
                sheet.write(i, j, value)
        out = StringIO()
        book.save(out)
        resp = make_response(out.getvalue())
    else:
        resp = make_response(results.content, results.status_code)
    resp.headers['Content-Type'] = 'application/vnd.ms-excel'
    now = datetime.now().isoformat().split('.')[0]
    resp.headers['Content-Disposition'] = 'attachment; filename=Crime_%s.xls' % now
    return resp

# expects GeoJSON object as a string
# client will need to use JSON.stringify() or similar

@app.route('/api/print/', methods=['POST'])
@crossdomain(origin="*")
def print_page():
    print_data = {
        'dimensions': request.form['dimensions'],
        'zoom': request.form['zoom'],
        'center': request.form['center'],
    }
    query = json.loads(request.form['query'])
    query['dataset_name'] = 'crimes_2001_to_present'
    results = requests.get('%s/v1/api/detail/' % WOPR_URL, params=query)
    if results.status_code == 200:
        cur = get_db().cursor()
        results = results.json()['objects']
        rs = []
        for r in results:
            cur.execute('select type from iucr where iucr = ?', (r['iucr'],))
            res = cur.fetchall()
            try:
                crime_type = res[0]['type']
            except IndexError:
                crime_type = 'other'
            if crime_type == 'sensitive':
                continue
            r['type'] = crime_type
            r['location'] = {
                'type': 'Point',
                'coordinates': [r['longitude'], r['latitude']]
            }
            rs.append(r)
        rs = sorted(rs, key=itemgetter('type'))
        point_overlays = []
        colors = {
            'violent': '#984ea3',
            'property': '#ff7f00',
            'quality': '#4daf4a',
            'other': '#377eb8',
        }
        for k,g in groupby(rs, key=itemgetter('type')):
            points = [r['location']['coordinates'] for r in list(g)]
            point_overlays.append(json.dumps({'color': colors[k], 'points': points}))
        print_data['point_overlays'] = point_overlays
        print_data['beat_overlays'] = []
        print_data['shape_overlays'] = []
        
        shapes_base_url = 'https://raw.githubusercontent.com/datamade/crimearound.us/master/data'

        if 'beat__in' in query.keys():
            # Need to get the actual shapes here
            beats = query['beat__in'].split(',')
            beat_path = '/tmp/%s.geojson'
            for beat in beats:
                if os.path.exists(beat_path % beat):
                    with open(beat_path % beat, 'r') as f:
                        print_data['shape_overlays'].append(f.read())
                else:
                    shape = requests.get('%s/beats/%s.geojson' % (shapes_base_url, beat))
                    with open(beat_path % beat, 'w') as f:
                        f.write(shape.content)
                    print_data['shape_overlays'].append(shape.content)
        
        if 'community_area__in' in query.keys():
            # Need to get the actual shapes here
            cas = query['community_area__in'].split(',')
            ca_path = '/tmp/%s.geojson'
            for ca in cas:
                if os.path.exists(ca_path % ca):
                    with open(ca_path % ca, 'r') as f:
                        print_data['shape_overlays'].append(f.read())
                else:
                    shape = requests.get('%s/community_areas/%s.geojson' % (shapes_base_url, ca.zfill(2)))
                    with open(ca_path % ca, 'w') as f:
                        f.write(shape.content)
                    print_data['shape_overlays'].append(shape.content)
        if 'location_geom__within' in query.keys():
            shape = query['location_geom__within']
            print_data['shape_overlays'].append(shape)
        
        print_data['units'] = 'pixels'
        
        pdf = requests.post('%s/api/' % LASCAUX_URL, data=print_data)
        
        now = datetime.now().isoformat().split('.')[0]
        filename = 'Crime_%s.pdf' % now

        with open('/tmp/%s' % filename, 'wb') as f:
            f.write(pdf.content)

        resp = make_response(json.dumps({'download': '/api/download/%s' % filename}))
        resp.headers['Content-Type'] = 'application/json'
        
    else:
        resp = make_response(results.content, results.status_code)
    return resp

@app.route('/api/download/<path:filename>')
def download_pdf(filename):
    return send_from_directory(directory='/tmp', filename=filename)


@app.route('/api/crime/', methods=['GET'])
@crossdomain(origin="*")
def crime():
    query = {
        'data_type': 'json',
        'limit': 2000,
        'order_by': 'obs_date,desc',
        'dataset_name': 'crimes_2001_to_present',
    }
    for k,v in request.args.items():
        query[k] = v
    locs = None
    if query.get('locations'):
        locs = query['locations'].split(',')
        descs = []
        for loc in locs:
            descs.extend(TYPE_GROUPS[loc])
        query['location_description__in'] = ','.join(descs)
        del query['locations']
    resp = {
        'code': 200,
        'meta': {
            'query': query,
            'total_results': 0,
            'totals_by_type': {
                'violent': 0,
                'property': 0,
                'quality': 0,
                'other': 0,
            },
        },
        'results': [],
    }
    results = requests.get('%s/v1/api/detail/' % WOPR_URL, params=query)
    if results.status_code == 200:
        cur = get_db().cursor()
        objs = results.json()['objects']
        resp['meta']['total_results'] = len(objs)
        if locs:
            resp['meta']['query']['locations'] = ','.join(locs)
            del resp['meta']['query']['location_description__in']
        for r in objs:
            cur.execute('select type from iucr where iucr = ?', (r['iucr'],))
            res = cur.fetchall()
            try:
                crime_type = res[0]['type']
            except IndexError:
                crime_type = 'other'
            if crime_type == 'sensitive':
                continue
            resp['meta']['totals_by_type'][crime_type] += 1
            r['crime_type'] = crime_type
            r['location'] = {
                'type': 'Point',
                'coordinates': [r['longitude'], r['latitude']]
            }
            r['community_area_name'] = COMM_AREA[str(r['community_area']).zfill(2)]
            resp['results'].append(r)
    else:
        resp['code'] = results.status_code
        resp['meta'] = results.json()['meta']
    resp = make_response(json.dumps(resp))
    resp.headers['Content-Type'] = 'application/json'
    return resp

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
