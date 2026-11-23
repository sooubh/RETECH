import re
from pathlib import Path

import click
import pymysql
from flask import current_app, g
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash

from .catalog import estimate_value


def connect(config):
    return pymysql.connect(
        host=config["MYSQL_HOST"],
        port=int(config["MYSQL_PORT"]),
        user=config["MYSQL_USER"],
        password=config["MYSQL_PASSWORD"],
        database=config["MYSQL_DATABASE"],
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=5,
    )


def get_db():
    if "db" not in g:
        g.db = connect(current_app.config)
    return g.db


def execute(sql, args=()):
    with get_db().cursor() as cursor:
        cursor.execute(sql, args)
        return cursor.lastrowid


def rows(sql, args=()):
    with get_db().cursor() as cursor:
        cursor.execute(sql, args)
        return cursor.fetchall()


def row(sql, args=()):
    with get_db().cursor() as cursor:
        cursor.execute(sql, args)
        return cursor.fetchone()


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def initialize_database():
    schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
    for statement in schema.split(";"):
        if statement.strip():
            execute(statement)
    get_db().commit()


@click.command("init-db")
@with_appcontext
def init_db_command():
    initialize_database()
    click.echo("MySQL tables are ready.")


@click.command("create-admin")
@click.option("--name", prompt=True)
@click.option("--email", prompt=True)
@click.password_option()
@with_appcontext
def create_admin(name, email, password):
    name, email = name.strip(), email.strip().lower()
    if not name or len(name) > 80 or not valid_email(email) or not 8 <= len(password) <= 128:
        raise click.ClickException("Enter a valid name, email and password (8–128 characters).")
    try:
        execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, 'admin')",
            (name, email, generate_password_hash(password)),
        )
    except pymysql.IntegrityError as error:
        raise click.ClickException("That email already belongs to an account.") from error
    get_db().commit()
    click.echo("Admin account created.")


def valid_email(email):
    return len(email) <= 254 and re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) is not None


@click.command("seed-demo")
@with_appcontext
def seed_demo():
    from secrets import token_urlsafe

    email = "demo-listings@retech.example"
    if row("SELECT id FROM users WHERE email = %s", (email,)):
        click.echo("Demo listings are already installed.")
        return
    seller = execute(
        "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, 'recycler')",
        ("RETECH Demo", email, generate_password_hash(token_urlsafe(32))),
    )
    listings = [
        ("Rechargeable battery pack", "batteries", "fair", "Demo listing for a used rechargeable battery pack with reduced capacity."),
        ("USB-C charger and cable", "chargers", "excellent", "Demo listing for a working USB-C wall charger with braided cable."),
        ("ThinkPad T480", "laptops", "good", "Demo listing for a working ThinkPad with light wear on the lid."),
        ("Samsung Galaxy A52", "phones", "good", "Demo listing for a working phone with minor scratches. Charger included."),
    ]
    for title, category, condition, description in listings:
        execute(
            """INSERT INTO listings (seller_id, title, category, device_condition, description, estimate)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (seller, title, category, condition, description, estimate_value(category, condition)),
        )
    get_db().commit()
    click.echo("Demo listings added.")


def register_commands(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(create_admin)
    app.cli.add_command(seed_demo)
