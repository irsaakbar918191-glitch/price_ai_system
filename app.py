import os
from flask import Flask, render_template
from flask_cors import CORS
from config import Config
from routes.auth_routes import auth_bp
from routes.product_routes import product_bp
from routes.upload_routes import upload_bp
from routes.search_routes import search_bp

def create_app():
    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates"
    )
    app.config.from_object(Config)

    CORS(app, supports_credentials=True)

    app.register_blueprint(auth_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(search_bp)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/login")
    def login_page():
        return render_template("login.html")

    @app.errorhandler(404)
    def not_found(e):
        return render_template("index.html"), 200

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=Config.PORT, debug=Config.DEBUG)