import os
from datetime import datetime, timedelta
import json
from urlparse import parse_qs, urlparse
from urllib import unquote
import xlwt
from cStringIO import StringIO
from itertools import groupby
from operator import itemgetter
from lookups import OK_FIELDS, OK_FILTERS, WORKSHEET_COLUMNS, TYPE_GROUPS
from pdfer.core import pdfer
import sqlite3

from flask import Flask, request, make_response, g
from raven.contrib.flask import Sentry

app = Flask(__name__)

app.url_map.strict_slashes = False

env = os.environ.get('PROJECTENV')

DEBUG = False

DATABASE = 'iucr_codes.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/api/lookups/')
def lookups():
    types = request.args.get('crime_types').split(',')
    locations = request.args.get('locations').split(',')
    results = {}
    if types:
        cur = get_db().execute('select iucr from iucr where type in ?', (types))
        results['crime_types'] = cur.fetchall()
        cur.close()
    resp = make_response(json.dumps(results))
    resp.headers['Content-Type'] = 'application/json'
    return resp


@app.route('/api/report/', methods=['GET'])
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

@app.route('/api/print/', methods=['GET'])
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

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 7777))
    app.run(host='0.0.0.0', port=port, debug=True)
