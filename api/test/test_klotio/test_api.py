import unittest
import unittest.mock
import klotio.unittest

import test_klotio.test_model
import os
import json
import yaml

import flask
import flask_restful
import opengui
import sqlalchemy.exc

import klotio.api


class Group(klotio.api.Group):
    APP = "unittest.klot.io"


class UnitTest(klotio.api.Model):

    SINGULAR = "unittest"
    PLURAL = "unittests"
    MODEL = test_klotio.test_model.UnitTest
    ORDER = [test_klotio.test_model.UnitTest.name]

    FIELDS = [
        {
            "name": "name"
        }
    ]

class UnitTestCL(UnitTest, klotio.api.RestCL):
    pass

class UnitTestRUD(UnitTest, klotio.api.RestRUD):
    pass


class TestRest(klotio.unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        cls.app = flask.Flask("klot-io-api")

        cls.app.mysql = test_klotio.test_model.MySQL()

        cls.app.redis = klotio.unittest.MockRedis("redis.com", 567)
        cls.app.channel = "zee"

        api = flask_restful.Api(cls.app)

        api.add_resource(klotio.api.Health, '/health')
        api.add_resource(Group, '/group')
        api.add_resource(UnitTestCL, '/unittest')
        api.add_resource(UnitTestRUD, '/unittest/<int:id>')

        cls.api = cls.app.test_client()

    def setUp(self):

        self.app.mysql.drop_database()
        self.app.mysql.create_database()

        self.session = self.app.mysql.session()
        self.sample = test_klotio.test_model.Sample(self.session)

        self.app.mysql.Base.metadata.create_all(self.app.mysql.engine)

    def tearDown(self):

        self.session.close()
        self.app.mysql.drop_database()


class TestAPI(TestRest):

    def test_require_session(self):

        mock_session = unittest.mock.MagicMock()
        self.app.mysql.session = unittest.mock.MagicMock(return_value=mock_session)

        @klotio.api.require_session
        def good():
            response = flask.make_response(json.dumps({"message": "yep"}))
            response.headers.set('Content-Type', 'application/json')
            response.status_code = 200
            return response

        self.app.add_url_rule('/good', 'good', good)

        response = self.api.get("/good")
        self.assertEqual(response.status_code, 200, response.json)
        self.assertEqual(response.json["message"], "yep")
        mock_session.close.assert_called_once_with()

        @klotio.api.require_session
        def bad():
            raise sqlalchemy.exc.InvalidRequestError("nope")

        self.app.add_url_rule('/bad', 'bad', bad)

        response = self.api.get("/bad")
        self.assertEqual(response.status_code, 500, response.json)
        self.assertEqual(response.json["message"], "session error")
        mock_session.rollback.assert_called_once_with()
        mock_session.close.assert_has_calls([
            unittest.mock.call(),
            unittest.mock.call()
        ])

        @klotio.api.require_session
        def ugly():
            raise Exception("whoops")

        self.app.add_url_rule('/ugly', 'ugly', ugly)

        response = self.api.get("/ugly")
        self.assertEqual(response.status_code, 500, response.json)
        self.assertEqual(response.json["message"], "whoops")
        mock_session.rollback.assert_called_once_with()
        mock_session.close.assert_has_calls([
            unittest.mock.call(),
            unittest.mock.call(),
            unittest.mock.call()
        ])

    def test_validate(self):

        fields = opengui.Fields(fields=[
            {
                "name": "name"
            },
            {
                "name": "yaml",
                "style": "textarea"
            }
        ])
        self.assertFalse(klotio.api.validate(fields))
        self.assertFields(fields, [
            {
                "name": "name",
                "errors": ["missing value"]
            },
            {
                "name": "yaml",
                "style": "textarea",
                "errors": ["missing value"]
            }
        ])

        fields = opengui.Fields(fields=[
            {
                "name": "name"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "value": "a: 1"
            }
        ])
        self.assertFalse(klotio.api.validate(fields))
        self.assertFields(fields, [
            {
                "name": "name",
                "errors": ["missing value"]
            },
            {
                "name": "yaml",
                "style": "textarea",
                "value": "a: 1"
            }
        ])

        fields = opengui.Fields(fields=[
            {
                "name": "name",
                "value": "yup"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "value": "a:1"
            }
        ])
        self.assertFalse(klotio.api.validate(fields))
        self.assertFields(fields, [
            {
                "name": "name",
                "value": "yup"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "value": "a:1",
                "errors": ["must be dict"]
            }
        ])

        fields = opengui.Fields(fields=[
            {
                "name": "name",
                "value": "yup"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "value": "a: 1"
            }
        ])
        self.assertTrue(klotio.api.validate(fields))
        self.assertFields(fields, [
            {
                "name": "name",
                "value": "yup"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "value": "a: 1"
            }
        ])

    def test_notify(self):

        def notify():
            klotio.api.notify({"a": 1})
            response = flask.make_response(json.dumps({"notify": True}))
            response.headers.set('Content-Type', 'application/json')
            response.status_code = 200
            return response

        self.app.add_url_rule('/notify', 'notify', notify)

        self.assertStatusValue(self.api.get("/notify"), 200, "notify", True)
        self.assertEqual(self.app.redis.messages, ['{"a": 1}'])


class TestHealth(TestRest):

    def test_get(self):

        self.assertEqual(self.api.get("/health").json, {"message": "OK"})


class TestGroup(TestRest):

    @unittest.mock.patch("requests.get")
    def test_get(self, mock_get):

        mock_get.return_value.json.return_value = [{
            "name": "unit",
            "url": "test"
        }]

        self.assertEqual(self.api.get("/group").json, {"group": [{
            "name": "unit",
            "url": "test"
        }]})

        mock_get.assert_has_calls([
            unittest.mock.call("http://api.klot-io/app/unittest.klot.io/member"),
            unittest.mock.call().raise_for_status(),
            unittest.mock.call().json()
        ])


class TestModel(TestRest):

    def test_validate(self):

        fields = opengui.Fields(fields=[
            {
                "name": "name",
                "value": "yup"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "value": "a: 1"
            }
        ])
        self.assertTrue(UnitTest.validate(fields))
        self.assertFields(fields, [
            {
                "name": "name",
                "value": "yup"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "value": "a: 1"
            }
        ])

    def test_retrieve(self):

        unit = self.sample.unittest("unit")

        @klotio.api.require_session
        def retrieve():
            response = flask.make_response(json.dumps({"retrieve": UnitTest.retrieve(unit.id).name}))
            response.headers.set('Content-Type', 'application/json')
            response.status_code = 200
            return response

        self.app.add_url_rule('/retrieve', 'retrieve', retrieve)

        self.assertStatusValue(self.api.get("/retrieve"), 200, "retrieve", "unit")

    def test_choices(self):

        unit = self.sample.unittest("unit")
        test = self.sample.unittest("test")

        @klotio.api.require_session
        def choices():
            response = flask.make_response(json.dumps({"choices": UnitTest.choices()}))
            response.headers.set('Content-Type', 'application/json')
            response.status_code = 200
            return response

        self.app.add_url_rule('/choices', 'choices', choices)

        self.assertStatusValue(self.api.get("/choices"), 200, "choices", [
            [test.id, unit.id],
            {str(test.id): "test", str(unit.id): "unit"}
        ])

    @unittest.mock.patch("requests.options")
    def test_derive(self, mock_options):

        mock_options.return_value.json.return_value = "yep"

        self.assertEqual(UnitTest.derive({"url": "sure"}), "yep")
        mock_options.assert_has_calls([
            unittest.mock.call("sure"),
            unittest.mock.call().raise_for_status(),
            unittest.mock.call().json()
        ])

        self.assertEqual(UnitTest.derive({"node": "sure"}), "yep")
        mock_options.assert_has_calls([
            unittest.mock.call("http://api.klot-io/node", params="sure"),
            unittest.mock.call().raise_for_status(),
            unittest.mock.call().json()
        ])

    @unittest.mock.patch("requests.options")
    def test_integrate(self, mock_options):

        def options(url, params=None):

            response = unittest.mock.MagicMock()

            if url == "sure":

                response.json.return_value = {
                    "fields": [
                        {
                            "integrate": {
                                "node": "yep"
                            }
                        },
                        {
                            "integrate": {
                                "url": "nope"
                            }
                        }
                    ]
                }

            elif url == "http://api.klot-io/node" and params == "yep":

                response.json.return_value = {
                    "name": "master"
                }

            elif url == "nope":

                response.raise_for_status.side_effect = Exception("whoops")

            return response

        mock_options.side_effect = options

        self.assertEqual(UnitTest.integrate({
            "integrate": {
                "url": "sure"
            }
        }), {
            "integrate": {
                "url": "sure"
            },
            "fields": [
                {
                    "integrate": {
                        "node": "yep"
                    },
                    "name": "master"
                },
                {
                    "integrate": {
                        "url": "nope"
                    },
                    "errors": ["failed to integrate: whoops"]
                }
            ]
        })

    @unittest.mock.patch("glob.glob")
    @unittest.mock.patch("klotio.api.open", create=True)
    @unittest.mock.patch("requests.options")
    def test_integrations(self, mock_options, mock_open, mock_glob):

        mock_glob.return_value = ["/opt/service/config/integration_unit.test_unittest.fields.yaml"]

        mock_open.side_effect = [
            unittest.mock.mock_open(read_data=yaml.safe_dump({
                "integrate": {
                    "url": "sure"
                }
            })).return_value
        ]

        def options(url, params=None):

            response = unittest.mock.MagicMock()

            if url == "sure":

                response.json.return_value = {
                    "fields": [
                        {
                            "integrate": {
                                "node": "yep"
                            }
                        },
                        {
                            "integrate": {
                                "url": "nope"
                            }
                        }
                    ]
                }

            elif url == "http://api.klot-io/node" and params == "yep":

                response.json.return_value = {
                    "name": "master"
                }

            elif url == "nope":

                response.raise_for_status.side_effect = Exception("whoops")

            return response

        mock_options.side_effect = options

        self.assertEqual(UnitTest.integrations(), [
            {
                "name": "unit.test",
                "integrate": {
                    "url": "sure"
                },
                "fields": [
                    {
                        "integrate": {
                            "node": "yep"
                        },
                        "name": "master"
                    },
                    {
                        "integrate": {
                            "url": "nope"
                        },
                        "errors": ["failed to integrate: whoops"]
                    }
                ]
            }
        ])

        mock_glob.assert_called_once_with("/opt/service/config/integration_*_unittest.fields.yaml")

        mock_open.assert_called_once_with("/opt/service/config/integration_unit.test_unittest.fields.yaml", "r")

    @unittest.mock.patch("glob.glob")
    @unittest.mock.patch("klotio.api.open", create=True)
    def test_request(self, mock_open, mock_glob):

        mock_glob.return_value = ["/opt/service/config/integration_unit.test_unittest.fields.yaml"]

        mock_open.side_effect = [
            unittest.mock.mock_open(read_data=yaml.safe_dump({
                "description": "Mock integraton",
                "fields": [{
                    "name": "integrate"
                }]
            })).return_value
        ]

        self.assertEqual(UnitTest.request({
            "a": 1,
            "unit.test": {
                "integrate": "yep"
            },
            "yaml": yaml.dump({"b": 2})
        }), {
            "a": 1,
            "data": {
                "b": 2,
                "unit.test": {
                    "integrate": "yep"
                }
            }
        })

    @unittest.mock.patch("glob.glob")
    @unittest.mock.patch("klotio.api.open", create=True)
    def test_response(self, mock_open, mock_glob):

        mock_glob.return_value = ["/opt/service/config/integration_unit.test_unittest.fields.yaml"]

        mock_open.side_effect = [
            unittest.mock.mock_open(read_data=yaml.safe_dump({
                "description": "Mock integraton",
                "fields": [{
                    "name": "integrate"
                }]
            })).return_value
        ]

        unitest = self.sample.unittest(
            "unit",
            data={
                "d": 4,
                "unit.test": {
                    "integrate": "yep"
                }
            }
        )

        self.assertEqual(UnitTest.response(unitest), {
            "id": unitest.id,
            "name": "unit",
            "unit.test": {
                "integrate": "yep"
            },
            "data": {
                "d": 4
            },
            "yaml": yaml.dump({"d": 4}, default_flow_style=False)
        })

    @unittest.mock.patch("glob.glob")
    @unittest.mock.patch("klotio.api.open", create=True)
    def test_responses(self, mock_open, mock_glob):

        mock_glob.return_value = ["/opt/service/config/integration_unit.test_unittest.fields.yaml"]

        mock_open.side_effect = [
            unittest.mock.mock_open(read_data=yaml.safe_dump({
                "description": "Mock integraton",
                "fields": [{
                    "name": "integrate"
                }]
            })).return_value
        ]

        unitest = self.sample.unittest(
            "unit",
            data={
                "d": 4,
                "unit.test": {
                    "integrate": "yep"
                }
            }
        )

        self.assertEqual(UnitTest.responses([unitest]), [{
            "id": unitest.id,
            "name": "unit",
            "unit.test": {
                "integrate": "yep"
            },
            "data": {
                "d": 4
            },
            "yaml": yaml.dump({"d": 4}, default_flow_style=False)
        }])


class TestRestCL(TestRest):

    @unittest.mock.patch("glob.glob")
    @unittest.mock.patch("klotio.api.open", create=True)
    def test_fields(self, mock_open, mock_glob):

        mock_glob.return_value = ["/opt/service/config/integration_unit.test_unittest.fields.yaml"]

        mock_open.side_effect = [
            unittest.mock.mock_open(read_data=yaml.safe_dump({"description": "integrate"})).return_value
        ]

        self.assertEqual(UnitTestCL.fields().to_list(), [
            {
                "name": "name"
            },
            {
                "name": "unit.test",
                "description": "integrate"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True
            }
        ])

        mock_glob.assert_called_once_with("/opt/service/config/integration_*_unittest.fields.yaml")

        mock_open.assert_called_once_with("/opt/service/config/integration_unit.test_unittest.fields.yaml", "r")

    def test_options(self):

        response = self.api.options("/unittest")

        self.assertStatusFields(response, 200, [
            {
                "name": "name"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True
            }
        ])

        response = self.api.options("/unittest", json={"unittest": {
            "nope": "bad"
        }})

        self.assertStatusFields(response, 200, [
            {
                "name": "name",
                "errors": ["missing value"]
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True
            }
        ], [
            "unknown field 'nope'"
        ])

        response = self.api.options("/unittest", json={"unittest": {
            "name": "yup"
        }})

        self.assertStatusFields(response, 200, [
            {
                "name": "name",
                "value": "yup"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True
            }
        ])

    def test_post(self):

        response = self.api.post("/unittest", json={
            "unittest": {
                "name": "unit",
                "data": {"a": 1}
            }
        })

        self.assertStatusModel(response, 201, "unittest", {
            "name": "unit",
            "data": {"a": 1}
        })

        unittest_id = response.json["unittest"]["id"]

    def test_get(self):

        self.sample.unittest("unit")
        self.sample.unittest("test")

        self.assertStatusModels(self.api.get("/unittest"), 200, "unittests", [
            {
                "name": "test"
            },
            {
                "name": "unit"
            }
        ])

class TestRestRUD(TestRest):

    @unittest.mock.patch("glob.glob")
    @unittest.mock.patch("klotio.api.open", create=True)
    def test_fields(self, mock_open, mock_glob):

        mock_glob.return_value = ["/opt/service/config/integration_unit.test_unittest.fields.yaml"]

        mock_open.side_effect = [
            unittest.mock.mock_open(read_data=yaml.safe_dump({"description": "integrate"})).return_value
        ]

        self.assertEqual(UnitTestRUD.fields().to_list(), [
            {
                "name": "id",
                "readonly": True
            },
            {
                "name": "name"
            },
            {
                "name": "unit.test",
                "description": "integrate"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True
            }
        ])

        mock_glob.assert_called_once_with("/opt/service/config/integration_*_unittest.fields.yaml")

        mock_open.assert_called_once_with("/opt/service/config/integration_unit.test_unittest.fields.yaml", "r")

    def test_options(self):

        unittest = self.sample.unittest("unit")

        response = self.api.options(f"/unittest/{unittest.id}")

        self.assertStatusFields(response, 200, [
            {
                "name": "id",
                "value": unittest.id,
                "original": unittest.id,
                "readonly": True
            },
            {
                "name": "name",
                "value": "unit",
                "original": "unit"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True,
                "value": '{}\n',
                "original": '{}\n'
            }
        ])

        response = self.api.options(f"/unittest/{unittest.id}", json={"unittest": {
            "nope": "bad"
        }})

        self.assertStatusFields(response, 200, [
            {
                "name": "id",
                "value": unittest.id,
                "original": unittest.id,
                "readonly": True
            },
            {
                "name": "name",
                "original": "unit",
                "errors": ["missing value"]
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True,
                "original": '{}\n'
            }
        ], [
            "unknown field 'nope'"
        ])

        response = self.api.options(f"/unittest/{unittest.id}", json={"unittest": {
            "name": "yup"
        }})

        self.assertStatusFields(response, 200, [
            {
                "name": "id",
                "value": unittest.id,
                "original": unittest.id,
                "readonly": True
            },
            {
                "name": "name",
                "value": "yup",
                "original": "unit"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True,
                "original": '{}\n'
            }
        ])

    def test_get(self):

        unittest = self.sample.unittest("unit")

        self.assertStatusModel(self.api.get(f"/unittest/{unittest.id}"), 200, "unittest", {
            "name": "unit"
        })

    def test_patch(self):

        unittest = self.sample.unittest("unit")

        self.assertStatusValue(self.api.patch(f"/unittest/{unittest.id}", json={
            "unittest": {
                "name": "unity"
            }
        }), 202, "updated", 1)

        self.assertStatusModel(self.api.get(f"/unittest/{unittest.id}"), 200, "unittest", {
            "name": "unity"
        })

    def test_delete(self):

        unittest = self.sample.unittest("unit")

        self.assertStatusValue(self.api.delete(f"/unittest/{unittest.id}"), 202, "deleted", 1)

        self.assertStatusModels(self.api.get("/unittest"), 200, "unittests", [])
