"""Small SQLite database helper for the RETECH college project."""

import re
import sqlite3
from pathlib import Path
from secrets import token_urlsafe

import click
from flask import current_app, g
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash

from .catalog import estimate_value
from .demo import DEMO_EMAIL, DEMO_LISTINGS, DEMO_NAME


def connect(config):
    """Open the local database; no MySQL or Docker service is required."""
    path = Path(config["DATABASE"]).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def get_db():
    if "db" not in g:
        g.db = connect(current_app.config)
    return g.db


def execute(sql, args=()):
    return get_db().execute(sql, args).lastrowid


def rows(sql, args=()):
    return [dict(item) for item in get_db().execute(sql, args).fetchall()]


def row(sql, args=()):
    item = get_db().execute(sql, args).fetchone()
    return dict(item) if item else None


def close_db(_error=None):
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def initialize_database():
    """Safe to call whenever the app starts; creates only missing tables."""
    schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
    get_db().executescript(schema)


def valid_email(email):
    return len(email) <= 254 and re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) is not None


def seed_demo_listings():
    """Add sample listings once; keep user changes on later launches."""
    execute(
        """INSERT OR IGNORE INTO users (name, email, password_hash, role)
           VALUES (?, ?, ?, 'recycler')""",
        (DEMO_NAME, DEMO_EMAIL, generate_password_hash(token_urlsafe(32))),
    )
    account = row("SELECT id, email, name, role FROM users WHERE email = ?", (DEMO_EMAIL,))
    if (account["email"], account["name"], account["role"]) != (DEMO_EMAIL, DEMO_NAME, "recycler"):
        raise click.ClickException("The reserved demo email belongs to another account.")

    seller_id = account["id"]
    existing = {item["title"] for item in rows("SELECT title FROM listings WHERE seller_id = ?", (seller_id,))}
    added = 0
    for title, (category, condition, description, _) in DEMO_LISTINGS.items():
        if title in existing:
            continue
        execute(
            """INSERT INTO listings (seller_id, title, category, device_condition, description, estimate)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (seller_id, title, category, condition, description, estimate_value(category, condition)),
        )
        added += 1
    get_db().commit()
    return added


@click.command("init-db")
@with_appcontext
def init_db_command():
    initialize_database()
    click.echo("SQLite tables are ready.")


@click.command("create-admin")
@click.option("--name", prompt=True)
@click.option("--email", prompt=True)
@click.password_option()
@with_appcontext
def create_admin(name, email, password):
    name, email = name.strip(), email.strip().lower()
    if not name or len(name) > 80 or not valid_email(email) or not 8 <= len(password) <= 128:
        raise click.ClickException("Enter a valid name, email and password (8-128 characters).")
    if email == DEMO_EMAIL:
        raise click.ClickException("Choose a different email address.")
    initialize_database()
    try:
        execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, 'admin')",
            (name, email, generate_password_hash(password)),
        )
    except sqlite3.IntegrityError as error:
        raise click.ClickException("That email already belongs to an account.") from error
    get_db().commit()
    click.echo("Admin account created.")


@click.command("seed-demo")
@with_appcontext
def seed_demo():
    initialize_database()
    added = seed_demo_listings()
    click.echo(f"Added {added} sample listings. {len(DEMO_LISTINGS) - added} were already installed.")


def register_commands(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(create_admin)
    app.cli.add_command(seed_demo)
