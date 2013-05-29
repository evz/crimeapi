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
    http://[url-endpoint]/?callback=myAwesomeCallback&[field_name]__[filter]=[value]
```

So, if you wanted to find all crimes reported between May 23, 2012 and June 25, 2012 it would look like this:

``` bash 
    http://[url-endpoint]/?callback=myAwesomeCallback&date__lte=1340582400&date__gte=1337731200
```

That’s right. I want timestamps, buddy. If you’re doing this from a client app, might I suggest [moment.js](http://momentjs.com)? It’s amazing and makes this kind of stuff pretty simple.

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