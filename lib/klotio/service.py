import os
import glob
import copy
import json
import yaml
import requests
import functools
import traceback

import flask
import flask_restful
import sqlalchemy.exc

import opengui


def require_session(endpoint):
    @functools.wraps(endpoint)
    def wrap(*args, **kwargs):

        flask.request.session = flask.current_app.mysql.session()

        try:

            response = endpoint(*args, **kwargs)

        except sqlalchemy.exc.InvalidRequestError:

            response = flask.make_response(json.dumps({
                "message": "session error",
                "traceback": traceback.format_exc()
            }))
            response.headers.set('Content-Type', 'application/json')
            response.status_code = 500

            flask.request.session.rollback()

        except Exception as exception:

            response = flask.make_response(json.dumps({"message": str(exception)}))
            response.headers.set('Content-Type', 'application/json')
            response.status_code = 500

        flask.request.session.close()

        return response

    return wrap

def validate(fields):

    valid = fields.validate()

    for field in fields.order:

        if field.name != "yaml" or field.value is None:
            continue

        if not isinstance(yaml.safe_load(field.value), dict):
            field.errors.append("must be dict")
            valid = False

    return valid

def notify(message):

    flask.current_app.redis.publish(flask.current_app.channel, json.dumps(message))

class Health(flask_restful.Resource):
    def get(self):
        return {"message": "OK"}

class Group(flask_restful.Resource):
    def get(self):
        response = requests.get(f"http://{os.environ['NODE_NAME']}:8083/app/{self.APP}/member")

        response.raise_for_status()

        return {"group": response.json()}

class Model:

    YAML = [
        {
            "name": "yaml",
            "style": "textarea",
            "optional": True
        }
    ]

    @staticmethod
    def validate(fields):

        return validate(fields)

    @classmethod
    def retrieve(cls, id):

        model = flask.request.session.query(
            cls.MODEL
        ).get(
            id
        )

        flask.request.session.commit()
        return model

    @classmethod
    def choices(cls):

        ids = []
        labels = {}

        for model in flask.request.session.query(
            cls.MODEL
        ).filter_by(
            **flask.request.args.to_dict()
        ).order_by(
            *cls.ORDER
        ).all():
            ids.append(model.id)
            labels[model.id] = model.name

        flask.request.session.commit()

        return (ids, labels)

    @staticmethod
    def derive(integrate):

        if "url" in integrate:
            response = requests.options(integrate["url"])
        elif "node" in integrate:
            response = requests.options(f"http://{os.environ['NODE_NAME']}:8083/node", params=integrate["node"])

        response.raise_for_status()

        return response.json()

    @classmethod
    def integrate(cls, integration):

        if "integrate" in integration:
            try:
                integration.update(cls.derive(integration["integrate"]))
            except Exception as exception:
                integration.setdefault("errors", [])
                integration["errors"].append(f"failed to integrate: {exception}")

        for field in integration.get("fields", []):
            cls.integrate(field)

        return integration

    @classmethod
    def integrations(cls):

        integrations = []

        for integration_path in sorted(glob.glob(f"/opt/service/config/integration_*_{cls.SINGULAR}.fields.yaml")):
            with open(integration_path, "r") as integration_file:
                integrations.append(cls.integrate({**{"name": integration_path.split("_")[1], **yaml.safe_load(integration_file)}}))

        return integrations

    @classmethod
    def request(cls, converted):

        values = {}

        integrations = opengui.Fields({}, {}, cls.integrations())

        for field in converted.keys():

            if field in integrations.names:
                values.setdefault("data", {})
                values["data"][field] = converted[field]
            elif field != "yaml":
                values[field] = converted[field]

        if "yaml" in converted:
            values.setdefault("data", {})
            values["data"].update(yaml.safe_load(converted["yaml"]))

        if "data" in converted:
            values.setdefault("data", {})
            values["data"].update(converted["data"])

        return values

    @classmethod
    def response(cls, model):

        converted = {
            "data": {}
        }

        integrations = opengui.Fields({}, {}, cls.integrations())

        for field in model.__table__.columns._data.keys():
            if field != "data":
                converted[field] = getattr(model, field)

        for field in model.data:
            if field in integrations.names:
                converted[field] = model.data[field]
            else:
                converted["data"][field] = model.data[field]

        converted["yaml"] = yaml.safe_dump(dict(converted["data"]), default_flow_style=False)

        return converted

    @classmethod
    def responses(cls, models):

        return [cls.response(model) for model in models]

class RestCL(flask_restful.Resource):

    @classmethod
    def fields(cls, values=None, originals=None):

        return opengui.Fields(values, originals=originals, fields=copy.deepcopy(cls.FIELDS + cls.integrations() + cls.YAML))

    @require_session
    def options(self):

        values = flask.request.json[self.SINGULAR] if flask.request.json and self.SINGULAR in flask.request.json else None

        fields = self.fields(values)

        if values is not None and not self.validate(fields):
            return {"fields": fields.to_list(), "errors": fields.errors}
        else:
            return {"fields": fields.to_list()}

    @require_session
    def post(self):

        model = self.MODEL(**self.request(flask.request.json[self.SINGULAR]))
        flask.request.session.add(model)
        flask.request.session.commit()

        return {self.SINGULAR: self.response(model)}, 201

    @require_session
    def get(self):

        models = flask.request.session.query(
            self.MODEL
        ).filter_by(
            **flask.request.args.to_dict()
        ).order_by(
            *self.ORDER
        ).all()
        flask.request.session.commit()

        return {self.PLURAL: self.responses(models)}

class RestRUD(flask_restful.Resource):

    ID = [
        {
            "name": "id",
            "readonly": True
        }
    ]

    @classmethod
    def fields(cls, values=None, originals=None):

        return opengui.Fields(values, originals=originals, fields=copy.deepcopy(cls.ID + cls.FIELDS + cls.integrations() + cls.YAML))

    @require_session
    def options(self, id):

        originals = self.response(self.retrieve(id))

        values = flask.request.json[self.SINGULAR] if flask.request.json and self.SINGULAR in flask.request.json else None

        fields = self.fields(values or originals, originals)

        if values is not None and not self.validate(fields):
            return {"fields": fields.to_list(), "errors": fields.errors}
        else:
            return {"fields": fields.to_list()}

    @require_session
    def get(self, id):

        return {self.SINGULAR: self.response(self.retrieve(id))}

    @require_session
    def patch(self, id):

        rows = flask.request.session.query(
            self.MODEL
        ).filter_by(
            id=id
        ).update(
            self.request(flask.request.json[self.SINGULAR])
        )
        flask.request.session.commit()

        return {"updated": rows}, 202

    @require_session
    def delete(self, id):

        rows = flask.request.session.query(
            self.MODEL
        ).filter_by(
            id=id
        ).delete()
        flask.request.session.commit()

        return {"deleted": rows}, 202
