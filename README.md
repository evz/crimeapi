# Yet another Chicago Crime API 

The main purpose of building this endpoint was to power this [site](http://www.crimearound.us) 
which needed a JSONP endpoint that could handle geospatial queries, a capability which does not 
exist in [any](https://data.cityofchicago.org/Public-Safety/Crimes-2001-to-present/ijzp-q8t2) 
of [the](http://api1.chicagopolice.org/clearpath/documentation) 
[other](https://github.com/newsapps/chicagocrime/blob/master/docs/api_docs.md) web APIs that are 
available. As of right now, I’m actually hoping to get someone else to take up this slack so that 
I don’t actually have to maintain this anymore.

## What’s inside?

The backend is MongoDB and has one big old collection that contains all of the crime data between January 1, 2001 
and a week ago for Chicago. The stuff you get back looks kinda looks [like this](https://github.com/evz/crimeapi/blob/master/sample-response.jsonp). 

So, it basically echos the query you sent back along with some other meta and then a list of results (in this case there’s only one match).

## How this sucker works

The backend is in MongoDB and I’m a Python/Django developer so I took what I knew about those two and 
made the thing you’re looking at now. Right now it only responds with JSONP so it requires that you provide 
a ``callback`` parameter as part of the request. Whether or not you actually use it in a client-side app after that 
is entirely up to you. Other than that, there aren’t any required fields. 

#### Limits

By default, you’re limited to 1000 records but you can pass in a ``limit`` parameter in the querystring to modify that. As of right now, there’s no upper limit but the web server is set to timeout after 60 seconds so if your query takes longer than that to fetch, you’re not going to get anything back. If you’d like to discuss this, I’d encourage [opening an issue](https://github.com/evz/crimeapi/issues). 

#### Constructing a query

If you’re familiar with [MongoDB](http://www.mongodb.org) and also familiar with [Tastypie](http://tastypieapi.org) this is, in the most basic sense, sort of like what might happen if you were able to wire those two things together (which I’m sure some clever person has done). The basic concept is to pass in the name of the field that you’d like to query, followed either by a filter (separated from the field name by two underscores) or by the value that you’re hoping to find in the database. In practice, that looks like this:

``` bash 
http://crime-weather.smartchicagoapps.org/api/crime/?callback=myAwesomeCallback&[field_name]__[filter]=[value]
```

So, if you wanted to find all crimes reported between May 23, 2012 and June 25, 2012 it would look like this:

``` bash 
http://crime-weather.smartchicagoapps.org/api/crime/?callback=myAwesomeCallback&date__lte=1340582400&date__gte=1337731200
```

That’s right. I want timestamps, buddy. If you’re doing this from a client app, might I suggest [moment.js](http://momentjs.com)? It’s amazing and makes this kind of stuff pretty simple.

If you just want to construct a query without a filter, just leave that part out. So, if you wanted to get crimes reported on May 23, 2012 and on June 25, 2012 you’d do this:

http://crime-weather.smartchicagoapps.org/api/crime/?callback=myAwesomeCallback&date=1340582400&date=1337731200

Although that would only return reports that were made exactly at midnight on those days (since the query is performed on both the date and time).

#### Queryable fields

I’m basically allowing queries on any fields that are present in the dataset and that make sense to perform queries on. If you’re familiar with the [dataset where all this crime data originates](https://data.cityofchicago.org/Public-Safety/Crimes-2001-to-present/ijzp-q8t2), you should find these fields rather familiar. 

``` bash 
year                    # a 4-digit year 
domestic                # Boolean telling whether or not the crime was in a domestic setting
case_number             # Chicago Police Department case number
id                      # Primary key carried over from Socrata 
primary_type            # Primary crime description
district                # Police district
arrest                  # Boolean telling whether or not an arrest was made
location                # GeoJSON Point of the location of the reported crime
community_area          # Chicago Community Area where the crime was reported
description             # Secondary description of the crime
beat                    # Police beat
date                    # Date and time the crime was reported as a timestamp
ward                    # Ward where the crime was reported
iucr                    # Illinois Uniform Crime Reporting (IUCR) Codes
location_description    # Location description
updated_on              # When the report was most recently updated
fbi_code                # FBI crime code
block                   # Street Block where the crime was reported
type                    # Index Crime type
```

A few things to note: 

* You can find out more about what I’m doing with the ``type`` field [here](http://crime.chicagotribune.com/chicago/about#crime-type-definition). I’m basically going with how the Tribune handles that so that there is less noise in general that you get with the responses.
* Learn more about IUCR codes and what they mean [here](https://data.cityofchicago.org/Public-Safety/Chicago-Police-Department-Illinois-Uniform-Crime-R/c7ck-438e).

#### Filtering queries

The filters that can be passed in along with the fields are these:

``` bash 
lt                  # Less than. Used for dates.
lte                 # Less than or equal to. Also for dates    
gt                  # Greater than. Yup, dates again
gte                 # Greater than or equal to. For dates.
near                # Used to find reports near a given point. See ‘Location queries’ below.
geoWithin           # Used to find reports within a given area. See ‘Location queries’ below.
in                  # Finds matches within an array of values
ne                  # Finds matches not equal to a given value
nin                 # Finds matches not within a given array of values
```

You can find more about the basic query operators [here](http://docs.mongodb.org/manual/reference/operator/).

#### Location queries

Finally, the good stuff. Any location based query expects ‘stringified’ GeoJSON as the lookup parameter. The excellent [JSON.js](https://github.com/douglascrockford/JSON-js) library has a pretty excellent tool for taking arbitrary JSON objects and turning them into strings (which is what I use). Some more modern browsers have an implementation of this already so, depending on your audience, you may be fine.

Depending on your geometry type, you’ll either use the ``near`` filter or the ``geoWithin`` filter to find what your after. If you’re looking for crime reports near a point, you’ll construct a GeoJSON Point object, stringify it and use a ``near`` filter to return what you’re after. If you’re looking for all reports within a given polygon, you’ll construct a GeoJSON Polygon, stringify it and use the ``geoWithin`` filter. Examples of what that might look like:

A GeoJSON Polygon...

``` javascript 
{
    "coordinates": [
        [
            [
                -87.66865611076355, 
                42.00809838577665
            ], 
            [
                -87.66855955123901, 
                42.004662333308616
            ], 
            [
                -87.66045928001404, 
                42.004869617835695
            ], 
            [
                -87.66071677207947, 
                42.00953334115145
            ], 
            [
                -87.6644504070282, 
                42.01010731423809
            ], 
            [
                -87.66865611076355, 
                42.00809838577665
            ]
        ]
    ], 
    "type": "Polygon"
}
```

...gets stringified and appended as a query parameter:

``` bash 
http://localhost:7777/api/crime/?callback=awesomeCallback&location__geoWithin=%7B%22type%22%3A%22Polygon%22%2C%22coordinates%22%3A%5B%5B%5B-87.66865611076355%2C42.00809838577665%5D%2C%5B-87.66855955123901%2C42.004662333308616%5D%2C%5B-87.66045928001404%2C42.004869617835695%5D%2C%5B-87.66071677207947%2C42.00953334115145%5D%2C%5B-87.6644504070282%2C42.01010731423809%5D%2C%5B-87.66865611076355%2C42.00809838577665%5D%5D%5D%7D&date__lte=1369285199&date__gte=1368594000&type=violent%2Cproperty&_=1369866788554
```

Looks a bit insane, but it works. 