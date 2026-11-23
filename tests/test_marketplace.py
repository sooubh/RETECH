import os
import re
import unittest
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from werkzeug.security import generate_password_hash

from retech import create_app
from retech.db import execute, get_db, initialize_database, row

PASSWORD = "test-password-123"
LISTING = {
    "title": "Integration ThinkPad",
    "category": "laptops",
    "device_condition": "good",
    "description": "The screen and keyboard work. Minor scratches.",
}


class MarketplaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database = os.getenv("RETECH_TEST_DATABASE", "")
        if not re.fullmatch(r"[a-zA-Z0-9_]+_test", database):
            raise RuntimeError("Set RETECH_TEST_DATABASE to a dedicated MySQL database ending in _test.")
        cls.app = create_app({"TESTING": True, "MYSQL_DATABASE": database, "SECRET_KEY": uuid4().hex})
        with cls.app.app_context():
            initialize_database()

    def setUp(self):
        self.domain = f"@{uuid4().hex}.example"

    def tearDown(self):
        pattern = ("%" + self.domain,)
        with self.app.app_context():
            execute(
                """DELETE t FROM transactions t JOIN buyback_requests r ON r.id = t.request_id
                   JOIN users u ON u.id = r.buyer_id WHERE u.email LIKE %s""",
                pattern,
            )
            execute("DELETE r FROM buyback_requests r JOIN users u ON u.id = r.buyer_id WHERE u.email LIKE %s", pattern)
            execute("DELETE l FROM listings l JOIN users u ON u.id = l.seller_id WHERE u.email LIKE %s", pattern)
            execute("DELETE FROM users WHERE email LIKE %s", pattern)
            get_db().commit()

    def post(self, client, path, data=None):
        with client.session_transaction() as session:
            session.setdefault("csrf_token", uuid4().hex)
            token = session["csrf_token"]
        return client.post(path, data={"csrf_token": token, **(data or {})})

    def register(self, name, role="member"):
        client = self.app.test_client()
        result = self.post(client, "/register", {
            "name": name, "role": role, "email": name.lower() + self.domain, "password": PASSWORD,
        })
        self.assertEqual(result.status_code, 302)
        return client

    def publish(self, seller, **fields):
        result = self.post(seller, "/listings/new", {**LISTING, **fields})
        self.assertEqual(result.status_code, 302)
        return result.location

    def request(self, client, path, **fields):
        result = self.post(client, path + "/request", fields)
        self.assertEqual(result.status_code, 302)
        with self.app.app_context():
            record = row(
                "SELECT id FROM buyback_requests WHERE listing_id = %s ORDER BY id DESC LIMIT 1",
                (path.rsplit("/", 1)[-1],),
            )
        return f"/requests/{record['id']}"

    def test_registration_login_and_csrf(self):
        client = self.register("Seller")
        self.assertIn(b"Your account is ready", client.get("/").data)
        with self.app.app_context():
            user = row("SELECT * FROM users WHERE email = %s", ("seller" + self.domain,))
            self.assertNotEqual(user["password_hash"], PASSWORD)
        self.assertEqual(client.post("/logout").status_code, 400)
        self.assertEqual(self.post(client, "/logout").status_code, 302)
        self.assertEqual(client.get("/listings/new").location, "/login?next=/listings/new")
        self.assertEqual(self.post(client, "/login", {"email": "seller" + self.domain, "password": "wrong"}).status_code, 401)
        self.assertEqual(self.post(client, "/register", {
            "name": "Seller", "email": "seller" + self.domain, "password": PASSWORD,
        }).status_code, 400)
        self.assertEqual(self.post(client, "/register", {
            "name": "Fake", "email": "fake" + self.domain, "password": PASSWORD, "role": "admin",
        }).status_code, 400)
        result = self.post(client, "/login?next=/listings/new", {"email": "seller" + self.domain, "password": PASSWORD})
        self.assertEqual(result.location, "/listings/new")
        self.assertEqual(client.get("/admin").status_code, 403)

    def test_listing_validation_edit_and_browse(self):
        seller = self.register("Seller")
        outsider = self.register("Outsider")
        self.assertEqual(self.post(seller, "/listings/new", {**LISTING, "category": "invalid"}).status_code, 400)
        self.assertEqual(seller.get("/estimate?category=invalid&condition=good").status_code, 400)
        self.assertEqual(seller.get("/estimate?category=laptops&condition=good").json, {"estimate": 9000})
        path = self.publish(seller, estimate=1)
        self.assertIn("₹9,000".encode(), seller.get(path).data)
        self.assertIn(b"Integration ThinkPad", outsider.get("/browse?q=ThinkPad&category=laptops&condition=good").data)
        self.assertNotIn(b"Integration ThinkPad", outsider.get("/browse?q=ThinkPad&category=phones").data)
        self.assertEqual(outsider.get(path + "/edit").status_code, 403)
        self.assertEqual(self.post(seller, path + "/request").status_code, 403)
        self.assertEqual(self.post(seller, path + "/edit", {**LISTING, "device_condition": "fair"}).status_code, 302)
        self.assertIn("₹5,400".encode(), seller.get("/my-listings").data)
        self.assertEqual(self.post(seller, path + "/archive").status_code, 302)
        self.assertEqual(outsider.get(path).status_code, 404)
        self.assertIn(b"Archived", seller.get("/my-listings").data)

    def test_buyback_lifecycle_and_history(self):
        seller = self.register("Seller")
        buyer = self.register("Buyer", "recycler")
        other = self.register("Other")
        path = self.publish(seller)
        request_path = self.request(buyer, path)
        self.assertEqual(self.post(buyer, path + "/request").status_code, 409)
        self.assertEqual(seller.get(path + "/edit").status_code, 409)
        other_path = self.request(other, path)
        self.assertNotIn(("buyer" + self.domain).encode(), seller.get("/requests").data)
        self.assertEqual(self.post(other, request_path + "/accept").status_code, 403)
        self.assertEqual(self.post(seller, request_path + "/complete").status_code, 409)
        self.assertEqual(self.post(seller, request_path + "/accept").status_code, 302)
        self.assertIn(b"Reserved", buyer.get(path).data)
        self.assertIn(("buyer" + self.domain).encode(), seller.get("/requests").data)
        self.assertIn(b"Declined", other.get("/requests").data)
        self.assertEqual(self.post(seller, other_path + "/accept").status_code, 409)
        self.assertEqual(self.post(seller, request_path + "/complete").location, "/history")
        self.assertEqual(self.post(seller, request_path + "/complete").status_code, 409)
        self.assertIn(b"No devices found", buyer.get("/browse?q=Integration+ThinkPad").data)
        for client in (seller, buyer):
            self.assertIn("₹9,000".encode(), client.get("/history").data)
        self.assertNotIn(b"Integration ThinkPad", other.get("/history").data)

    def test_exchange_cancel_and_complete(self):
        seller = self.register("Seller")
        buyer = self.register("Buyer")
        path = self.publish(seller)
        missing = self.post(buyer, path + "/request", {"kind": "exchange"})
        self.assertEqual(missing.location, path)
        self.assertIn(b"Describe what", buyer.get(path).data)
        initial = self.request(buyer, path, kind="exchange", exchange_details="USB-C dock")
        self.assertEqual(self.post(seller, initial + "/decline").status_code, 302)
        withdrawn = self.request(buyer, path, kind="exchange", exchange_details="USB-C dock")
        self.assertEqual(self.post(buyer, withdrawn + "/cancel").status_code, 302)
        exchange = self.request(buyer, path, kind="exchange", exchange_details="USB-C dock")
        self.assertEqual(self.post(seller, exchange + "/accept").status_code, 302)
        self.assertEqual(self.post(buyer, exchange + "/cancel").status_code, 302)
        self.assertIn(b"Available", seller.get(path).data)
        exchange = self.request(buyer, path, kind="exchange", exchange_details="USB-C dock")
        self.assertEqual(self.post(seller, exchange + "/accept").status_code, 302)
        self.assertEqual(self.post(seller, exchange + "/complete").location, "/history")
        self.assertIn(b"USB-C dock", buyer.get("/history").data)

    def test_admin_moderation(self):
        seller = self.register("Seller")
        buyer = self.register("Buyer")
        path = self.publish(seller)
        self.request(buyer, path)
        with self.app.app_context():
            execute(
                "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, 'admin')",
                ("Admin", "admin" + self.domain, generate_password_hash(PASSWORD)),
            )
            get_db().commit()
        admin = self.app.test_client()
        self.post(admin, "/login", {"email": "admin" + self.domain, "password": PASSWORD})
        self.assertIn(b"Admin dashboard", admin.get("/admin").data)
        self.assertEqual(self.post(buyer, path + "/archive").status_code, 403)
        self.assertEqual(self.post(admin, path + "/archive").location, "/admin")
        self.assertIn(b"Archived", admin.get("/admin").data)
        self.assertIn(b"Declined", buyer.get("/requests").data)

    def test_competing_accepts_create_only_one_reservation(self):
        first_seller_client = self.register("Seller")
        second_seller_client = self.app.test_client()
        self.post(second_seller_client, "/login", {"email": "seller" + self.domain, "password": PASSWORD})
        first_buyer = self.register("First")
        second_buyer = self.register("Second")
        path = self.publish(first_seller_client)
        first = self.request(first_buyer, path)
        second = self.request(second_buyer, path)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [
                pool.submit(self.post, first_seller_client, first + "/accept"),
                pool.submit(self.post, second_seller_client, second + "/accept"),
            ]
            self.assertEqual(sorted(result.result().status_code for result in results), [302, 409])
        self.assertIn(b"Reserved", first_seller_client.get(path).data)
