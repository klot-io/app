import unittest
import unittest.mock

import sqlalchemy
import sqlalchemy.ext.mutable
import sqlalchemy_jsonfield

import klotio.models


class MySQL(klotio.models.MySQL):
    DATABASE = "klotio"


class UnitTest(klotio.models.MySQL.Base):

    __tablename__ = "unittest"

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String(64), nullable=False)
    data = sqlalchemy.Column(
        sqlalchemy.ext.mutable.MutableDict.as_mutable(
            sqlalchemy_jsonfield.JSONField(enforce_string=True,enforce_unicode=False)
        ),
        nullable=False,
        default=dict
    )

    sqlalchemy.schema.UniqueConstraint('name', name='label')

    def __repr__(self):
        return "<UnitTest(name='%s')>" % (self.name)


class Sample:

    def __init__(self, session):

        self.session = session

    def unittest(self, name, data=None):

        unittests = self.session.query(UnitTest).filter_by(name=name).all()

        if unittests:
            return unittests[0]

        unittest = UnitTest(name=name, data=data)
        self.session.add(unittest)
        self.session.commit()

        return unittest


class TestMySQL(unittest.TestCase):

    maxDiff = None

    def setUp(self):

        self.mysql = MySQL()
        self.session = self.mysql.session()
        self.mysql.drop_database()
        self.mysql.create_database()
        self.mysql.Base.metadata.create_all(self.mysql.engine)

    def tearDown(self):

        self.session.close()
        self.mysql.drop_database()

    def test_MySQL(self):

        self.assertEqual(str(self.session.get_bind().url), "mysql+pymysql://root@klotio-app-mysql:3306/klotio")

    def test_UnitTest(self):

        self.session.add(UnitTest(
            name="unit"
        ))
        self.session.commit()

        unittest = self.session.query(UnitTest).one()
        self.assertEqual(str(unittest), "<UnitTest(name='unit')>")
        self.assertEqual(unittest.name, "unit")

        unittest.name = 'test'
        self.session.commit()
        unittest = self.session.query(UnitTest).one()
        self.assertEqual(unittest.name, "test")
