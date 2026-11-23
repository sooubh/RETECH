"""Run RETECH locally with: python app.py"""

from retech import create_app
from retech.db import initialize_database, seed_demo_listings

app = create_app()

with app.app_context():
    initialize_database()
    seed_demo_listings()

if __name__ == "__main__":
    app.run(debug=True)
