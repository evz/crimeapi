import os
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.dialects.postgresql import TIMESTAMP, DOUBLE_PRECISION
from geoalchemy2 import Geometry
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref

Base = declarative_base()

class Crime(Base):
    __tablename__ = 'crime'
    id = Column(Integer)
    case_number = Column(String(length=10))
    date = Column(TIMESTAMP)
    block = Column(String(length=50))
    iucr = Column(String(length=10))
    primary_type = Column(String(length=100))
    description = Column(String(length=100))
    location_description = Column(String(length=50))
    arrest = Column(Boolean)
    domestic = Column(Boolean)
    beat = Column(String(length=10))
    district = Column(String(length=5))
    ward = Column(Integer)
    community_area = Column(String(length=10))
    fbi_code = Column(String(length=10))
    x_coordinate = Column(Integer)
    y_coordinate = Column(Integer)
    year = Column(Integer)
    updated_on = Column(TIMESTAMP, default=None)
    latitude = Column(DOUBLE_PRECISION(precision=53))
    longitude = Column(DOUBLE_PRECISION(precision=53))
    location = Column(String(length=50))
    geom = Column(Geometry(geometry_type=u'POINT', srid=4326))

    def __repr__(self):
        return '<Crime %r (%r)>' % (self.block, self.orig_date.strftime('%Y/%m/%d %H:%M'))


if __name__ == '__main__':
    from sqlalchemy import create_engine
    engine = create_engine(os.environ['CRIME_DB'])
