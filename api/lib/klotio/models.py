import os

import yaml
import pymysql
import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.ext.declarative
import flask_jsontools

class MySQL(object):
    """
    Main class for interacting with Nandy in MySQL
    """

    def __init__(self):

        self.database = os.environ.get("DATABASE", self.DATABASE)

        self.engine = sqlalchemy.create_engine(
            f"mysql+pymysql://root@{os.environ['MYSQL_HOST']}:{os.environ['MYSQL_PORT']}/{self.database}"
        )
        self.maker = sqlalchemy.orm.sessionmaker(bind=self.engine)

    def session(self):

        return self.maker()

    @classmethod
    def create_database(cls):

        database = os.environ.get("DATABASE", cls.DATABASE)
        connection = pymysql.connect(host=os.environ['MYSQL_HOST'], user='root')

        try:

            with connection.cursor() as cursor:
                cursor._defer_warnings = True
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database}")

            connection.commit()

        finally:

            connection.close()

    @classmethod
    def drop_database(cls):

        database = os.environ.get("DATABASE", cls.DATABASE)
        connection = pymysql.connect(host=os.environ['MYSQL_HOST'], user='root')

        try:

            with connection.cursor() as cursor:
                cursor._defer_warnings = True
                cursor.execute(f"DROP DATABASE IF EXISTS {database}")

            connection.commit()

        finally:

            connection.close()

    Base = sqlalchemy.ext.declarative.declarative_base(cls=(flask_jsontools.JsonSerializableBase))
