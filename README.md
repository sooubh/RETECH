# RETECH — E-Waste Buyback College Project

RETECH is a beginner-friendly marketplace for unused electronics. It uses **Python, Flask, HTML, CSS, JavaScript and SQLite**.

**No Docker, MySQL server, cloud account, or paid API keys are needed.** The database is created automatically in a local file.

## Run on your laptop

Install **Python 3.10+**, open a terminal in this folder, then run:

**Windows (PowerShell)**

    py -m venv .venv
    .venv\Scripts\Activate.ps1
    python -m pip install -r requirements.txt
    python app.py

If PowerShell blocks activation, use .venv\Scripts\python.exe instead of python in the following commands.

**macOS / Linux**

    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install -r requirements.txt
    python app.py

Open **http://127.0.0.1:5000/** in your browser.

The first launch creates instance/retech.sqlite3, creates the four tables and adds 12 sample electronics. Restarting does not erase your data. Press **Ctrl+C** to stop the server.

## Five-minute college demonstration

1. Register a **Seller** account.
2. Choose **List a device**, enter a laptop/phone, and select its condition. The estimated price appears automatically.
3. Open a private/incognito browser window and register a second **Buyer** account.
4. As Buyer, find the Seller's item in **Marketplace** and send a Buyback or Exchange request.
5. As Seller, open **Requests**, accept the request, and mark it complete.
6. Open **Buyback history** in both accounts and show the saved transaction.

The 12 sample devices are **for browsing only**. Create a new seller listing for the actual buyback demo.

Optional: create an admin account with this command and follow the prompts:

    python -m flask --app retech create-admin

The Admin tab then shows totals, listings and requests.

## Main features

- Registration, login, logout; passwords stored as secure hashes.
- Add, edit, search, filter and archive devices.
- Automatic estimates by category and condition.
- Buyback and exchange requests with accept, decline and cancel actions.
- Completion and transaction history.
- Admin dashboard and responsive frontend.

## Easy code structure

    RETECH/
    ├── app.py                   # Start the website
    ├── requirements.txt         # Python packages
    ├── retech/
    │   ├── __init__.py          # Flask configuration
    │   ├── views.py             # Pages and buyback actions
    │   ├── db.py                # Simple SQLite database helper
    │   ├── schema.sql           # Four SQL tables
    │   ├── catalog.py           # Prices and categories
    │   ├── demo.py              # 12 sample devices
    │   ├── templates/           # HTML
    │   └── static/              # CSS, JS, images
    ├── tests/
    └── instance/                # Database created locally (gitignored)

**Architecture:** Web browser → Flask route → SQLite database → HTML page.

**Example price formula:** base price × condition percentage / 100.
A good-condition laptop: ₹12,000 × 75% = **₹9,000**.

## Check the project

Run the integration suite; it uses a temporary SQLite database and does not touch saved data:

    python -m unittest discover -s tests -v

## Troubleshooting

- **Python not found:** Install Python and enable Add to PATH (on Windows, try py app.py).
- **Flask missing:** Install requirements inside the virtual environment.
- **Port 5000 busy:** Stop another Flask server before running app.py again.
- **Fresh project data:** Stop the server, delete instance/retech.sqlite3 and restart. This removes all accounts, listings and history.

## Viva and submission notes

There are four database tables: **users, listings, buyback_requests and transactions**. The marketplace is a local educational demo; it does not process payments or provide actual courier/recycling pickup. Old MySQL data is **not** automatically migrated to SQLite.

For public deployment, disable Flask debug mode, use HTTPS and configure RETECH_SECRET_KEY with a strong secret and RETECH_SECURE_COOKIE=1. Local development creates a persistent secret automatically.

Photo sources and licenses: [Credits](retech/static/images/credits.txt).
