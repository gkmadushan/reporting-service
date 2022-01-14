from sqlalchemy import create_engine, engine_from_config
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()

DB_USERNAME = os.getenv('DB_USERNAME')
DB_PASSWORD = os.getenv('DB_PASSWORD')
SQLALCHEMY_DB_URL = "postgresql://%s:%s@db" % (DB_USERNAME, DB_PASSWORD)
config = {'db.url': SQLALCHEMY_DB_URL, 'db.echo': 'True'}

engine = engine_from_config(config, prefix='db.', pool_size=50, max_overflow=0)
engine.dialect.supports_sane_rowcount = engine.dialect.supports_sane_multi_rowcount = False
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    except:
        db.close()
        raise HTTPException(status_code=500, detail="Database exception")


def get_db_config():
    return SQLALCHEMY_DB_URL
