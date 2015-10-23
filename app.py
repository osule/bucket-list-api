from flask.ext.api import FlaskAPI
from flask.ext.api.exceptions import APIException, \
    AuthenticationFailed, NotFound, NotAcceptable
from flask import request
from models import db, BucketList, BucketListItem
from tools import list_object_transform
import auth


class CredentialsRequired(APIException):
    """Raises a 202 accepted when the user first accesses GET /login"""
    status_code = 202
    detail = "Make a POST to '/login' with your credentials to begin a session"


def create_app(config_module="config.DevelopmentConfig"):
    app = FlaskAPI(__name__)
    app.config.from_object(config_module)
    db.init_app(app)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "GET":
            raise CredentialsRequired()
        username = request.form.get("username")
        password = request.form.get("password")

        if auth.check_auth(username, password):
            return {
                "message": [
                    auth.MESSAGES["login"],
                    {
                        "available endpoints":
                        app.config.get('AVAILABLE_ENDPOINTS')
                    }
                ],
                "token": auth.tokenize(username, password)
            }
        else:
            raise AuthenticationFailed()

    @app.route("/logout", methods=["GET"])
    @auth.requires_auth
    def logout():
        if auth.logout():
            return {"message": auth.MESSAGES["logout"]}
        raise NotFound()

    @app.route("/bucketlists", methods=["POST", "GET"])
    @auth.requires_auth
    def bucketlist():
        user_id = auth.get_current_user_id()
        if request.method == "GET":
            query = BucketList.query.filter(
                user_id == user_id)
            limit = request.args.get('limit')
            if query.all():
                if not limit:
                    result_data = list_object_transform(query.all())
                else:
                    if 0 <= int(limit) <= 100:
                        result_data = list_object_transform(
                            BucketListItem.query.limit(limit)
                        )
                    else:
                        raise NotAcceptable()
                return {'message': result_data}
            raise NotFound()

        else:
            name = request.form.get("name")
            a_bucketlist = BucketList(created_by=user_id, name=name)
            db.session.add(a_bucketlist)
            db.session.commit()
            return {
                "message": "Bucketlist was created successfully",
                "bucketlist": a_bucketlist.to_json()}, 201

    @app.route("/bucketlists/<id>", methods=["GET", "DELETE", "PUT"])
    @auth.requires_auth
    @auth.belongs_to_user
    def actionable_bucketlist(id, **kwargs):
        bucketlist = kwargs.get('bucketlist')
        if request.method == "DELETE":
            db.session.delete(bucketlist)
            db.session.commit()
            return {"message": "Bucketlist was deleted successfully"}, 200

        elif request.method == "PUT":
            name = request.form.get("name")
            bucketlist.name = name
            bucketlist.id = id
            db.session.commit()
        return bucketlist.to_json(), 200

    @app.route("/bucketlists/<id>/items", methods=["POST"])
    @auth.requires_auth
    @auth.belongs_to_user
    def create_bucketlist_item(id, **kwargs):
        name = request.form.get('name')
        done = request.form.get('done')
        bucketlistitem = BucketListItem(bucketlist_id=id, name=name, done=done)
        db.session.add(bucketlistitem)
        db.session.commit()
        return {
            "message": "Bucketlist item was created successfully",
            "bucketlistitem": bucketlistitem.to_json()}, 201

    @app.route(
        "/bucketlists/<id>/items/<item_id>",
        methods=["GET", "PUT", "DELETE"])
    @auth.requires_auth
    @auth.belongs_to_user
    @auth.belongs_to_bucketlist
    def actionable_bucketlist_item(id, item_id, **kwargs):
        bucketlistitem = kwargs.get('bucketlistitem')
        if request.method == "DELETE":
            db.session.delete(bucketlistitem)
            db.session.commit()
            return {"message": "Bucketlist item was deleted successfully"}, 200

        elif request.method == "PUT":
            name = request.form.get("name")
            done = request.form.get("done")
            bucketlistitem.name = name
            bucketlistitem.done = done
            bucketlistitem.id = item_id
            bucketlistitem.bucketlist_id = id
            db.session.commit()
        return bucketlistitem.to_json(), 200
    return app

if __name__ == '__main__':
    bucket_list_app = create_app()
    bucket_list_app.run(debug=True)
