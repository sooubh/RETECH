import os
from secrets import compare_digest, token_urlsafe

from dotenv import load_dotenv
from flask import Flask, abort, g, render_template, request, session

from .catalog import CATEGORIES, CONDITIONS, money
from .db import register_commands, row


def create_app(config=None):
    load_dotenv()
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("RETECH_SECRET_KEY"),
        MYSQL_HOST=os.getenv("MYSQL_HOST", "127.0.0.1"),
        MYSQL_PORT=os.getenv("MYSQL_PORT", "3306"),
        MYSQL_DATABASE=os.getenv("MYSQL_DATABASE", "retech"),
        MYSQL_USER=os.getenv("MYSQL_USER", "retech"),
        MYSQL_PASSWORD=os.getenv("MYSQL_PASSWORD"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("RETECH_SECURE_COOKIE") == "1",
        MAX_CONTENT_LENGTH=16 * 1024,
    )
    if config:
        app.config.update(config)
    if not app.config["SECRET_KEY"] or not app.config["MYSQL_PASSWORD"]:
        raise RuntimeError("Set RETECH_SECRET_KEY and MYSQL_PASSWORD in .env. See README.md.")

    register_commands(app)
    from .views import bp

    app.register_blueprint(bp)
    app.jinja_env.filters["money"] = money
    app.jinja_env.globals.update(categories=CATEGORIES, conditions=CONDITIONS)

    def csrf_token():
        if "csrf_token" not in session:
            session["csrf_token"] = token_urlsafe(32)
        return session["csrf_token"]

    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def prepare_request():
        g.user = None
        if request.method == "POST":
            expected = session.get("csrf_token", "")
            supplied = request.form.get("csrf_token", "")
            if not expected or not compare_digest(expected.encode(), supplied.encode()):
                abort(400, "Your form expired. Reload the page and try again.")
        user_id = session.get("user_id")
        if user_id is not None:
            g.user = row("SELECT id, name, email, role FROM users WHERE id = %s", (user_id,))

    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(409)
    @app.errorhandler(413)
    def handle_error(error):
        return render_template("error.html", error=error), error.code

    return app
