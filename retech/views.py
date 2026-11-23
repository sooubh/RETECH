from functools import wraps

import sqlite3
from flask import (
    Blueprint, abort, flash, g, jsonify, redirect, render_template, request, session, url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from .catalog import CATEGORIES, CONDITIONS, estimate_value
from .db import execute, get_db, row, rows, valid_email
from .demo import DEMO_EMAIL

bp = Blueprint("site", __name__)


def login_required(view):
    @wraps(view)
    def wrapped(**kwargs):
        if g.user is None:
            next_path = request.path if request.method == "GET" else None
            return redirect(url_for("site.login", next=next_path))
        return view(**kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(**kwargs):
        if g.user["role"] != "admin":
            abort(403)
        return view(**kwargs)

    return wrapped


def after_authentication():
    path = request.args.get("next", "")
    if path.startswith("/") and not path.startswith("//") and "\\" not in path and path.isprintable():
        return redirect(path)
    return redirect(url_for("site.home"))


@bp.get("/")
def home():
    listings = rows(
        """SELECT l.*, u.email = ? COLLATE BINARY AS sample
           FROM listings l JOIN users u ON u.id = l.seller_id
           WHERE l.status = 'available' ORDER BY l.id DESC LIMIT 4""",
        (DEMO_EMAIL,),
    )
    return render_template("home.html", listings=listings)


@bp.get("/browse")
def browse():
    query = request.args.get("q", "").strip()[:100]
    category = request.args.get("category", "")
    condition = request.args.get("condition", "")
    page = max(1, min(request.args.get("page", 1, type=int), 1000000))
    conditions = ["l.status = 'available'"]
    args = []
    if query:
        conditions.append("(instr(lower(l.title), lower(?)) > 0 OR instr(lower(l.description), lower(?)) > 0)")
        args.extend((query, query))
    if category in CATEGORIES:
        conditions.append("l.category = ?")
        args.append(category)
    if condition in CONDITIONS:
        conditions.append("l.device_condition = ?")
        args.append(condition)
    where = " AND ".join(conditions)
    total = row(f"SELECT COUNT(*) AS count FROM listings l WHERE {where}", args)["count"]
    listings = rows(
        f"""SELECT l.*, u.email = ? COLLATE BINARY AS sample
            FROM listings l JOIN users u ON u.id = l.seller_id
            WHERE {where} ORDER BY l.id DESC LIMIT 12 OFFSET ?""",
        (DEMO_EMAIL, *args, (page - 1) * 12),
    )
    return render_template(
        "browse.html", listings=listings, total=total, page=page, has_next=page * 12 < total,
        query=query, category=category, condition=condition,
    )


@bp.route("/register", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(url_for("site.home"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "member")
        error = None
        if not 1 <= len(name) <= 80:
            error = "Enter your name (up to 80 characters)."
        elif not valid_email(email):
            error = "Enter a valid email address."
        elif email == DEMO_EMAIL:
            error = "Enter a different email address."
        elif not 8 <= len(password) <= 128:
            error = "Use a password between 8 and 128 characters."
        elif role not in ("member", "recycler"):
            error = "Select an account type."
        if error is None:
            try:
                user_id = execute(
                    "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
                    (name, email, generate_password_hash(password), role),
                )
                get_db().commit()
            except sqlite3.IntegrityError:
                error = "An account already exists for that email."
            else:
                session.clear()
                session["user_id"] = user_id
                flash("Your account is ready.", "success")
                return after_authentication()
        return render_template("auth.html", registering=True, error=error), 400
    return render_template("auth.html", registering=True)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("site.home"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = row("SELECT id, password_hash FROM users WHERE email = ?", (email,)) if valid_email(email) else None
        if user and len(password) <= 128 and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            return after_authentication()
        return render_template("auth.html", error="That email and password don’t match."), 401
    return render_template("auth.html")


@bp.post("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("site.home"))


@bp.get("/estimate")
def estimate():
    category = request.args.get("category")
    condition = request.args.get("condition")
    if category not in CATEGORIES or condition not in CONDITIONS:
        return jsonify(error="Choose a category and condition."), 400
    return jsonify(estimate=estimate_value(category, condition))


def listing_form(listing=None):
    data = listing or {}
    error = None
    if request.method == "POST":
        data = {
            field: request.form.get(field, "").strip()
            for field in ("title", "category", "device_condition", "description")
        }
        if not 1 <= len(data["title"]) <= 100:
            error = "Enter a device name (up to 100 characters)."
        elif data["category"] not in CATEGORIES or data["device_condition"] not in CONDITIONS:
            error = "Select a category and a condition."
        elif not 1 <= len(data["description"]) <= 1500:
            error = "Describe the device in up to 1,500 characters."
        else:
            fields = (
                data["title"], data["category"], data["device_condition"], data["description"],
                estimate_value(data["category"], data["device_condition"]),
            )
            if listing:
                listing_id = listing["id"]
                execute(
                    """UPDATE listings SET title = ?, category = ?, device_condition = ?,
                       description = ?, estimate = ? WHERE id = ?""",
                    (*fields, listing_id),
                )
            else:
                listing_id = execute(
                    """INSERT INTO listings (title, category, device_condition, description, estimate, seller_id)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (*fields, g.user["id"]),
                )
            get_db().commit()
            flash("Listing updated." if listing else "Your device is listed.", "success")
            return redirect(url_for("site.listing_detail", listing_id=listing_id))
    return render_template("listing_form.html", listing=listing, data=data, error=error), 400 if error else 200


@bp.route("/listings/new", methods=["GET", "POST"])
@login_required
def new_listing():
    return listing_form()


@bp.get("/listings/<int:listing_id>")
def listing_detail(listing_id):
    listing = row(
        """SELECT l.*, u.name AS seller, u.role AS seller_role,
                  u.email = ? COLLATE BINARY AS sample
           FROM listings l JOIN users u ON u.id = l.seller_id WHERE l.id = ?""",
        (DEMO_EMAIL, listing_id),
    )
    if not listing:
        abort(404)
    active_request = None
    can_edit = False
    is_owner = g.user and g.user["id"] == listing["seller_id"]
    is_admin = g.user and g.user["role"] == "admin"
    if is_owner and listing["status"] == "available":
        can_edit = not row(
            "SELECT id FROM buyback_requests WHERE listing_id = ? AND status = 'pending' LIMIT 1",
            (listing_id,),
        )
    if g.user and not is_owner:
        active_request = row(
            """SELECT id FROM buyback_requests WHERE listing_id = ? AND buyer_id = ?
               AND status IN ('pending', 'accepted', 'completed')""",
            (listing_id, g.user["id"]),
        )
    if listing["status"] == "archived" and not (is_owner or is_admin):
        abort(404)
    return render_template(
        "listing_detail.html", listing=listing, is_owner=is_owner, can_edit=can_edit,
        active_request=active_request,
    )


def lock_listing(listing_id):
    # SQLite serializes write actions so two buyers cannot reserve one device.
    if request.method == "POST" and not get_db().in_transaction:
        get_db().execute("BEGIN IMMEDIATE")
    listing = row("SELECT * FROM listings WHERE id = ?", (listing_id,))
    if not listing:
        abort(404)
    return listing


@bp.route("/listings/<int:listing_id>/edit", methods=["GET", "POST"])
@login_required
def edit_listing(listing_id):
    listing = lock_listing(listing_id)
    if g.user["id"] != listing["seller_id"]:
        abort(403)
    if listing["status"] != "available" or row(
        "SELECT id FROM buyback_requests WHERE listing_id = ? AND status = 'pending' LIMIT 1",
        (listing_id,),
    ):
        abort(409, "Resolve pending requests before editing an available listing.")
    return listing_form(listing)


@bp.post("/listings/<int:listing_id>/archive")
@login_required
def archive_listing(listing_id):
    listing = lock_listing(listing_id)
    is_admin = g.user["role"] == "admin"
    if g.user["id"] != listing["seller_id"] and not is_admin:
        abort(403)
    if listing["status"] != "available":
        abort(409, "Only available listings can be archived.")
    execute("UPDATE listings SET status = 'archived' WHERE id = ?", (listing_id,))
    execute(
        "UPDATE buyback_requests SET status = 'declined' WHERE listing_id = ? AND status = 'pending'",
        (listing_id,),
    )
    get_db().commit()
    flash("Listing archived.", "success")
    return redirect(url_for("site.admin" if is_admin else "site.my_listings"))


@bp.get("/my-listings")
@login_required
def my_listings():
    listings = rows("SELECT * FROM listings WHERE seller_id = ? ORDER BY id DESC", (g.user["id"],))
    return render_template("my_listings.html", listings=listings)


@bp.post("/listings/<int:listing_id>/request")
@login_required
def make_request(listing_id):
    listing = lock_listing(listing_id)
    if listing["seller_id"] == g.user["id"]:
        abort(403)
    if listing["status"] != "available":
        abort(409, "This listing is no longer available.")
    seller = row("SELECT email FROM users WHERE id = ?", (listing["seller_id"],))
    if seller["email"] == DEMO_EMAIL:
        abort(409, "Sample listings are for browsing. Choose a device listed by a member to send a request.")
    if row(
        """SELECT id FROM buyback_requests WHERE listing_id = ? AND buyer_id = ?
           AND status = 'pending' LIMIT 1""",
        (listing_id, g.user["id"]),
    ):
        abort(409, "You already have a pending request for this device.")
    kind = request.form.get("kind", "buyback")
    details = request.form.get("exchange_details", "").strip()
    if kind not in ("buyback", "exchange"):
        abort(400, "Choose a request type.")
    if kind == "exchange" and not 1 <= len(details) <= 300:
        flash("Describe what you’re offering in exchange in up to 300 characters.", "error")
        return redirect(url_for("site.listing_detail", listing_id=listing_id))
    execute(
        """INSERT INTO buyback_requests (listing_id, buyer_id, kind, offer, exchange_details)
           VALUES (?, ?, ?, ?, ?)""",
        (
            listing_id, g.user["id"], kind, listing["estimate"] if kind == "buyback" else 0,
            details if kind == "exchange" else "",
        ),
    )
    get_db().commit()
    flash("Request sent to the seller.", "success")
    return redirect(url_for("site.requests_view"))


@bp.get("/requests")
@login_required
def requests_view():
    requests = rows(
        """SELECT r.*, l.title, l.category, l.seller_id,
                  seller.name AS seller, seller.email AS seller_email,
                  buyer.name AS buyer, buyer.email AS buyer_email
           FROM buyback_requests r
           JOIN listings l ON l.id = r.listing_id
           JOIN users seller ON seller.id = l.seller_id
           JOIN users buyer ON buyer.id = r.buyer_id
           WHERE (l.seller_id = ? OR r.buyer_id = ?) AND r.status <> 'completed'
           ORDER BY r.id DESC""",
        (g.user["id"], g.user["id"]),
    )
    return render_template("requests.html", requests=requests)


@bp.post("/requests/<int:request_id>/<action>")
@login_required
def manage_request(request_id, action):
    request_listing = row("SELECT listing_id FROM buyback_requests WHERE id = ?", (request_id,))
    if not request_listing:
        abort(404)
    listing = lock_listing(request_listing["listing_id"])
    buyback = row("SELECT * FROM buyback_requests WHERE id = ?", (request_id,))
    seller = listing["seller_id"] == g.user["id"]
    buyer = buyback["buyer_id"] == g.user["id"]
    if not seller and not buyer:
        abort(403)
    updates = {
        "accept": (seller, "pending", "available", "accepted"),
        "decline": (seller, "pending", "available", "declined"),
        "cancel": (buyer or (seller and buyback["status"] == "accepted"), buyback["status"], listing["status"], "cancelled"),
        "complete": (seller, "accepted", "reserved", "completed"),
    }
    if action not in updates:
        abort(404)
    allowed, expected_request, expected_listing, new_status = updates[action]
    if not allowed:
        abort(403)
    if action == "cancel" and buyback["status"] not in ("pending", "accepted"):
        abort(409, "Only open requests can be cancelled.")
    if buyback["status"] != expected_request or listing["status"] != expected_listing:
        abort(409, "This request has already changed.")

    execute("UPDATE buyback_requests SET status = ? WHERE id = ?", (new_status, request_id))
    if action == "accept":
        execute("UPDATE listings SET status = 'reserved' WHERE id = ?", (listing["id"],))
        execute(
            """UPDATE buyback_requests SET status = 'declined'
               WHERE listing_id = ? AND status = 'pending'""",
            (listing["id"],),
        )
    elif action == "cancel" and buyback["status"] == "accepted":
        execute("UPDATE listings SET status = 'available' WHERE id = ?", (listing["id"],))
    elif action == "complete":
        execute("UPDATE listings SET status = 'sold' WHERE id = ?", (listing["id"],))
        execute("INSERT INTO transactions (request_id, amount) VALUES (?, ?)", (request_id, buyback["offer"]))
    get_db().commit()
    flash(f"Request {new_status}.", "success")
    return redirect(url_for("site.history" if action == "complete" else "site.requests_view"))


@bp.get("/history")
@login_required
def history():
    transactions = rows(
        """SELECT t.*, l.title, r.kind, r.exchange_details, l.seller_id,
                  seller.name AS seller, buyer.name AS buyer
           FROM transactions t
           JOIN buyback_requests r ON r.id = t.request_id
           JOIN listings l ON l.id = r.listing_id
           JOIN users seller ON seller.id = l.seller_id
           JOIN users buyer ON buyer.id = r.buyer_id
           WHERE l.seller_id = ? OR r.buyer_id = ?
           ORDER BY t.id DESC""",
        (g.user["id"], g.user["id"]),
    )
    return render_template("history.html", transactions=transactions)


@bp.get("/admin")
@admin_required
def admin():
    counts = row(
        """SELECT (SELECT COUNT(*) FROM users) AS users,
                  (SELECT COUNT(*) FROM listings WHERE status = 'available') AS listings,
                  (SELECT COUNT(*) FROM buyback_requests WHERE status IN ('pending', 'accepted')) AS requests,
                  (SELECT COUNT(*) FROM transactions) AS transactions"""
    )
    listings = rows(
        """SELECT l.*, u.name AS seller FROM listings l JOIN users u ON u.id = l.seller_id
           ORDER BY l.id DESC"""
    )
    requests = rows(
        """SELECT r.*, l.title, u.name AS buyer FROM buyback_requests r
           JOIN listings l ON l.id = r.listing_id JOIN users u ON u.id = r.buyer_id ORDER BY r.id DESC"""
    )
    return render_template("admin.html", counts=counts, listings=listings, requests=requests)
