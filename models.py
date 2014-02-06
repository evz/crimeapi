import os
from sqlalchemy import Column, Integer, String, Text, DateTime, Table,\
    ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref

Base = declarative_base()

if __name__ == '__main__':
    from sqlalchemy import create_engine
    engine = create_engine(os.environ['CRIME_DB'])
