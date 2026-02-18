from flask import Flask, Blueprint, jsonify, redirect, request
from flask_restplus import Api
from ma import ma
from db import db
from werkzeug.middleware.proxy_fix import ProxyFix

from resources.store import Store, StoreList, store_ns, stores_ns
from resources.item import Item, ItemList, items_ns, item_ns
from marshmallow import ValidationError

app = Flask(__name__)

# Make Flask respect X-Forwarded-* headers from the ALB (important for https in swagger)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Optional, but helps swagger/flask generate https links when behind a proxy
app.config["PREFERRED_URL_SCHEME"] = "https"
app.config["SWAGGER_SUPPORTED_SUBMIT_METHODS"] = ["get", "post", "put", "delete"]

bluePrint = Blueprint("api", __name__, url_prefix="/api")
api = Api(bluePrint, doc="/doc/", title="Sample Flask-RestPlus Application")
app.register_blueprint(bluePrint)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["PROPAGATE_EXCEPTIONS"] = True

# Register resources
item_ns.add_resource(Item, "/<int:id>")
items_ns.add_resource(ItemList, "")
store_ns.add_resource(Store, "/<int:id>")
stores_ns.add_resource(StoreList, "")

# Force https for swagger.json when UI is opened via https (fix mixed-content in browser)
@bluePrint.before_request
def force_https_for_swagger():
    xf_proto = request.headers.get("X-Forwarded-Proto", "")
    if request.path.startswith("/api/swagger.json") and xf_proto == "https" and not request.is_secure:
        request.environ["wsgi.url_scheme"] = "https"

# Some UIs try to fetch /api/doc/swagger.json - redirect it to the real swagger json
@bluePrint.route("/doc/swagger.json")
def swagger_json_for_ui():
    return redirect("/api/swagger.json", code=302)

@app.before_first_request
def create_tables():
    db.create_all()

@api.errorhandler(ValidationError)
def handle_validation_error(error):
    return jsonify(error.messages), 400

api.add_namespace(item_ns)
api.add_namespace(items_ns)
api.add_namespace(store_ns)
api.add_namespace(stores_ns)

@app.route("/")
def health():
    return "OK", 200

if __name__ == "__main__":
    db.init_app(app)
    ma.init_app(app)
    # Keep port 80 as you had (ALB terminates TLS and forwards HTTP)
    app.run(host="0.0.0.0", port=5000)
