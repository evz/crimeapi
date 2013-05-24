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
and a week ago for Chicago. The stuff you get back looks kinda looks like this: 

``` javascript
    {
        "code": 200, 
        "meta": {
            "query": {
                "date": {
                    "$gte": {
                        "$date": 1368162000000
                    }, 
                    "$lte": {
                        "$date": 1368853199000
                    }
                }, 
                "location": {
                    "$geoWithin": {
                        "$geometry": {
                            "coordinates": [
                                [
                                    [
                                        -87.6674222946167, 
                                        42.00782733501583
                                    ], 
                                    [
                                        -87.66729354858398, 
                                        42.00581036220167
                                    ], 
                                    [
                                        -87.66204714775085, 
                                        42.00582630690156
                                    ], 
                                    [
                                        -87.66302347183228, 
                                        42.00837740741237
                                    ], 
                                    [
                                        -87.6674222946167, 
                                        42.00782733501583
                                    ]
                                ]
                            ], 
                            "type": "Polygon"
                        }
                    }
                }, 
                "type": {
                    "$in": [
                        "violent", 
                        "property", 
                        "quality"
                    ]
                }
            }, 
            "total_results": 1
        }, 
        "results": [
            {
                "_id": {
                    "$oid": "519f878e3c002ed20d7896b0"
                }, 
                "arrest": false, 
                "beat": "2431", 
                "block": "014XX W MORSE AVE", 
                "case_number": "HW277368", 
                "community_area": "1", 
                "date": {
                    "$date": 1368721800000
                }, 
                "description": "TO VEHICLE", 
                "district": "024", 
                "domestic": false, 
                "fbi_code": "14", 
                "id": "9132606", 
                "iucr": "1320", 
                "latitude": "42.00778004584161", 
                "location": {
                    "coordinates": [
                        -87.66690898033619, 
                        42.00778004584161
                    ], 
                    "type": "Point"
                }, 
                "location_description": "PARKING LOT/GARAGE(NON.RESID.)", 
                "longitude": "-87.66690898033619", 
                "primary_type": "CRIMINAL DAMAGE", 
                "type": "quality", 
                "updated_on": {
                    "$date": 1368923980000
                }, 
                "ward": "49", 
                "x_coordinate": "1165371", 
                "y_coordinate": "1946130", 
                "year": "2013"
            }
        ], 
        "status": "ok"
    }
```

So, it basically echos the query you sent back along with some other meta and then a list of results (in this case there’s only one match).

## How this sucker works

The backend is in MongoDB and I’m a Python/Django developer so I took what I knew about those two and 
made the thing you’re looking at now. Right now it only responds with JSONP so it requires that you provide 
a ``callback`` parameter as part of the request. Whether or not you actually use it in a client-side app after that 
is entirely up to you. Other than that, not
