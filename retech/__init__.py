import os
from pathlib import Path
from secrets import compare_digest, token_urlsafe

from dotenv import load_dotenv
from flask import Flask, abort, g, render_template, request, session

from .catalog import CATEGORIES, CONDITIONS, money
from .db import register_commands, row
from .demo import listing_photo


def create_app(config=None):
    load_dotenv()
    app = Flask(__name__)
    # Store a generated local secret so sessions survive app restarts.
    secret = os.getenv("RETECH_SECRET_KEY")
    if not secret:
        secret_file = Path(app.instance_path) / ".secret-key"
        secret_file.parent.mkdir(parents=True, exist_ok=True)
        if not secret_file.exists():
            secret_file.write_text(token_urlsafe(48), encoding="utf-8")
            secret_file.chmod(0o600)
        secret = secret_file.read_text(encoding="utf-8").strip()
    app.config.from_mapping(
        SECRET_KEY=secret,
        DATABASE=os.getenv("RETECH_DATABASE") or str(Path(app.instance_path) / "retech.sqlite3"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("RETECH_SECURE_COOKIE") == "1",
        MAX_CONTENT_LENGTH=16 * 1024,
    )
    if config:
        app.config.update(config)
    register_commands(app)
    from .views import bp

    app.register_blueprint(bp)
    app.jinja_env.filters["money"] = money
    app.jinja_env.globals.update(categories=CATEGORIES, conditions=CONDITIONS, listing_photo=listing_photo)

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
            g.user = row("SELECT id, name, email, role FROM users WHERE id = ?", (user_id,))

    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(409)
    @app.errorhandler(413)
    def handle_error(error):
        return render_template("error.html", error=error), error.code

    return app
