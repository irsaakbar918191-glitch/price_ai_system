import os
from flask import Flask, jsonify, render_template
from config import Config
from routes.auth_routes import auth_bp
from routes.upload_routes import upload_bp
from routes.search_routes import search_bp
from routes.product_routes import product_bp


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)

    # Registering Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(product_bp)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/login")
    def login_page():
        return render_template("login.html")

    @app.get("/health")
    def health_check():
        return jsonify({"status": "ok", "service": "price-ai-system"}), 200

    return app


app = create_app()


if __name__ == "__main__":
    # Safe port and debug defaults
    port = int(getattr(Config, "PORT", 5000))
    debug = bool(getattr(Config, "DEBUG", True))

    app.run(host="0.0.0.0", port=port, debug=debug)