"""Basic first-run checks without a database server."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from retech import create_app
from retech.db import initialize_database, row, seed_demo_listings


class QuickStartTests(unittest.TestCase):
    def test_local_first_run_and_restart(self):
        with TemporaryDirectory() as folder:
            settings = {
                "TESTING": True,
                "DATABASE": str(Path(folder) / "retech.sqlite3"),
                "SECRET_KEY": "temporary-unit-test-secret",
            }
            first = create_app(settings)
            with first.app_context():
                initialize_database()
                self.assertEqual(seed_demo_listings(), 12)
                self.assertEqual(row("SELECT COUNT(*) AS count FROM listings")["count"], 12)

            client = first.test_client()
            self.assertEqual(client.get("/").status_code, 200)
            self.assertEqual(client.get("/browse").status_code, 200)
            self.assertEqual(
                client.get("/estimate?category=laptops&condition=good").json,
                {"estimate": 9000},
            )

            restarted = create_app(settings)
            with restarted.app_context():
                initialize_database()
                self.assertEqual(seed_demo_listings(), 0)
                self.assertEqual(row("SELECT COUNT(*) AS count FROM listings")["count"], 12)


if __name__ == "__main__":
    unittest.main()
