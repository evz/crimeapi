import pymongo
import requests
import csv
from datetime import datetime, timedelta
import os
import json
from bson import json_util
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from utils import make_meta
from operator import itemgetter
from itertools import groupby
from cStringIO import StringIO

AWS_KEY = os.environ['AWS_ACCESS_KEY']
AWS_SECRET = os.environ['AWS_SECRET_KEY']

def dump_by_temp(crime, weather):
    grouped = []
    for temp in range(-30, 120):
        days = [d['DATE'] for d in weather.find({'FAHR_MAX': {'$gt': temp, '$lt': temp + 1}})]
        if days:
            grouped.append({'temp': temp, 'days': days})
    for group in grouped:
        crime_summary = []
        for day in group['days']:
            crimes = [c for c in crime.find({'date': {'$gt': day, '$lt': day + timedelta(hours=24)}})]
            crime_summary.append(make_meta(crimes))
        summary = {
            'total': 0,
            'detail': {
                'arson': 0,
                'assault': 0,
                'battery': 0,
                'burglary': 0,
                'crim_sexual_assault': 0,
                'criminal_damage': 0,
                'criminal_trespass': 0,
                'deceptive_practice': 0,
                'domestic_violence': 0,
                'gambling': 0,
                'homicide': 0,
                'interfere_with_public_officer': 0,
                'interference_with_public_officer': 0,
                'intimidation' :0,
                'kidnapping': 0,
                'liquor_law_violation': 0,
                'motor_vehicle_theft': 0,
                'narcotics': 0,
                'non_criminal': 0,
                'non_criminal_subject_specified': 0,
                'obscenity': 0,
                'offense_involving_children': 0,
                'offenses_involving_children': 0,
                'other_narcotic_violation': 0,
                'other_offense': 0,
                'prostitution': 0,
                'public_indecency': 0,
                'public_peace_violation': 0,
                'ritualism': 0,
                'robbery': 0,
                'sex_offense': 0,
                'stalking': 0,
                'theft': 0,
                'weapons_violation': 0,
            }
        }
        for cr in crime_summary:
            summary['total'] += cr['total']['value']
            for detail in cr['detail']:
                summary['detail'][detail['key']] += detail['value']
        group['summary'] = summary
    organizer = []
    for group in grouped:
        organizer.append({'key': 'total', 'temp': group['temp'], 'average': float(group['summary']['total']) / float(len(group['days'])), 'day_count': len(group['days'])})
        for k,v in group['summary']['detail'].items():
            organizer.append({'key': k, 'temp': group['temp'], 'average': float(v) / float(len(group['days'])), 'day_count': len(group['days'])})
    output = []
    organizer = sorted(organizer, key=itemgetter('key'))
    for k,g in groupby(organizer, key=itemgetter('key')):
        output.append({'key': k, 'data': list(g)})
    for group in output:
        s3conn = S3Connection(AWS_KEY, AWS_SECRET)
        bucket = s3conn.get_bucket('crime.static-eric.com')
        k = Key(bucket)
        name = 'data/weather/%s.json' % group['key']
        k.key = name
        k.set_contents_from_string(json.dumps(group, indent=4))
        k = k.copy(k.bucket.name, k.name, {'Content-Type':'application/json'})
        k.set_acl('public-read')
        print 'Uploaded %s' % name

def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)

def dumpit(crime, weather, start_date=datetime(2013, 4, 25), end_date=datetime.now()):
    s3conn = S3Connection(AWS_KEY, AWS_SECRET)
    bucket = s3conn.get_bucket('crime.static-eric.com')
    for single_date in daterange(start_date, end_date):
        weat = [w for w in weather.find({'DATE': single_date})]
        if len(weat) > 0:
            midnight = single_date.replace(hour=0).replace(minute=0)
            one_til = single_date.replace(hour=23).replace(minute=59)
            crimes = [c for c in crime.find({'date': {'$gt': midnight, '$lt': one_til}})]
            if len(crimes) > 0:
                out = {
                    'weather': {
                        'CELSIUS_MIN': weat[0]['CELSIUS_MIN'],
                        'CELSIUS_MAX': weat[0]['CELSIUS_MAX'],
                        'FAHR_MAX': weat[0]['FAHR_MAX'],
                        'FAHR_MIN': weat[0]['FAHR_MIN'],
                    }, 
                    'meta': make_meta(crimes),
                    'geojson': {
                        'type': 'FeatureCollection',
                        'features': [{
                            'type': 'Feature',
                            'geometry': f.get('location'),
                            'properties': {
                                'title': f.get('primary_type').title(),
                                'description': f.get('description').title(), 
                                'key': '_'.join(f.get('primary_type').lower().split()),
                                'arrest': f.get('arrest'),
                                'beat': f.get('beat'),
                                'block': f.get('block'),
                                'community_area': f.get('community_area'),
                                'district': f.get('district'),
                                'domestic': f.get('domestic'),
                                'location_desc': f.get('location_description'),
                                'ward': f.get('ward')
                            }
                        } for f in crimes]
                    }
                }
                # f = open('data/%s/%s/%s.json' % (single_date.year, single_date.month, single_date.day), 'wb')
                # f.write(json_util.dumps(out, indent=4, sort_keys=True))
                # f.close()
                k = Key(bucket)
                k.key = 'data/%s/%s/%s.json' % (single_date.year, single_date.month, single_date.day)
                k.set_contents_from_string(json_util.dumps(out, indent=4))
                k = k.copy(k.bucket.name, k.name, {'Content-Type':'application/json'})
                k.set_acl('public-read')
                print 'Uploaded %s' % k.key

def dump_to_csv(start_date, end_date, out_name):
    c = pymongo.MongoClient()
    db = c['chicago']
    db.authenticate(os.environ['CHICAGO_MONGO_USER'], password=os.environ['CHICAGO_MONGO_PW'])
    crime = db['crime']
    weather = db['weather']
    all_rows = []
    for date in daterange(start_date, end_date):
        midnight = date.replace(hour=0).replace(minute=0)
        one_til = date.replace(hour=23).replace(minute=59)
        days_crimes = list(crime.find({'date': {'$gt': midnight, '$lt': one_til}}))
        if days_crimes:
            meta = make_meta(days_crimes)
            days_weather = weather.find_one({'DATE': date})
            out = {
                'date': datetime.strftime(date, '%m-%d-%Y'),
                'temp_max': weather['FAHR_MAX'],
                'total_count': meta['total']['value'],
            }
            fieldnames = sorted(out.keys())
            for category in meta['detail']:
                fieldnames.append(category['key'])
                out[category['key']] = category['value']
            all_rows.append(out)
    out_f = StringIO()
    writer = csv.DictWriter(out_f, fieldnames=fieldnames)
    writer.writerow(dict( (n,n) for n in fieldnames ))
    writer.writerows(all_rows)
    s3conn = S3Connection(AWS_KEY, AWS_SECRET)
    bucket = s3conn.get_bucket('crime.static-eric.com')
    k = Key(bucket)
    k.key = 'data/weather/%s.csv' % out_name
    k.set_contents_from_string(out_f.getvalue())
    k = k.copy(k.bucket.name, k.name, {'Content-Type':'text/csv'})
    k.set_acl('public-read')

def dump_aggregate(crime_type):
    pipe = [
        {
            '$match': {
                'primary_type': crime_type
            }
        }, 
        {
            '$group': {
                '_id': {
                    'month_reported': {
                        '$month': '$date'
                    }, 
                    'year_reported': {
                        '$year': '$date'
                    }
                }, 
                'count': {'$sum': 1}
            }
        }, 
        {
            '$sort': {'count': -1}
        }
    ]
    results = crime.aggregate(pipe)
    output = []
    for result in results['result']:
        date = '-'.join([result['month_reported'], result['year_reported']])
        output.append({'date': date, 'count': result['count']})
    out_f = StringIO()
    fieldnames = output[0].keys()
    writer = csv.DictWriter(out_f, fieldnames=fieldnames)
    writer.writerow(dict( (n,n) for n in fieldnames ))
    writer.writerows(output)
    s3conn = S3Connection(AWS_KEY, AWS_SECRET)
    bucket = s3conn.get_bucket('crime.static-eric.com')
    k = Key(bucket)
    k.key = 'data/aggregates/%s.csv' % crime_type
    k.set_contents_from_string(out_f.getvalue())
    k = k.copy(k.bucket.name, k.name, {'Content-Type':'text/csv'})
    k.set_acl('public-read')

if __name__ == '__main__':
    import sys
    c = pymongo.MongoClient()
    db = c['chicago']
    db.authenticate(os.environ['CHICAGO_MONGO_USER'], password=os.environ['CHICAGO_MONGO_PW'])
    crime = db['crime']
    weather = db['weather']
    dumpit(crime, weather)
    dump_by_temp(crime, weather)
    if len(sys.argv) > 2:
        start, end = sys.argv[1:3]
        name = sys.argv[3]
        dump_to_csv(start, end, name)
