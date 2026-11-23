# RETECH · E-waste buyback marketplace

RETECH connects people who have unused electronics with buyers and recycling partners. An individual or partner can publish a device, get an estimate in INR, and send a buyback or exchange request. After the seller accepts, both participants can arrange the handoff by email. The seller records completion and both accounts can see the transaction in **Buyback history**.

The frontend uses HTML, CSS, and JavaScript. Flask renders pages and manages requests, authentication, and price calculation. MySQL 8.4 stores the accounts, listings, requests, and transactions.

## Run RETECH in Cloud

Run the commands from the project directory, `/workspace/RETECH` in the prepared Cloud workspace. For a fresh Cloud setup, extract the source ZIP under `/workspace` and open the resulting `RETECH` directory in your terminal. Docker mounts the schema file from this directory. Use Python 3.12 or later and Docker Compose v2.

### 1. Install the Python dependencies

```sh
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
```

### 2. Prepare the environment

The command below creates `.env` with separate generated secrets for the app, MySQL app user, and MySQL root user. It preserves an existing `.env` and its database credentials.

```sh
python - <<'PY'
from pathlib import Path
from secrets import token_hex

path = Path(".env")
if not path.exists():
    content = Path(".env.example").read_text()
    for key in ("RETECH_SECRET_KEY", "MYSQL_PASSWORD", "MYSQL_ROOT_PASSWORD"):
        content = content.replace(f"{key}=\n", f"{key}={token_hex(32)}\n")
    path.write_text(content)
    path.chmod(0o600)
PY
```

| Setting | Default or purpose |
| --- | --- |
| `RETECH_SECRET_KEY` | Generated secret for Flask session cookies and form protection |
| `RETECH_SECURE_COOKIE` | `0` for the local HTTP preview. Set to `1` for HTTPS hosting |
| `MYSQL_HOST` / `MYSQL_PORT` | `127.0.0.1` / `3306` for the included Compose service |
| `MYSQL_DATABASE` / `MYSQL_USER` | `retech` / `retech` |
| `MYSQL_PASSWORD` | Generated password used by Flask to connect as the app user |
| `MYSQL_ROOT_PASSWORD` | Separate password used by Compose to provision MySQL and by the root user for database administration |

### 3. Start MySQL and load the sample marketplace

```sh
docker compose up -d --wait db
.venv/bin/flask --app retech init-db
.venv/bin/flask --app retech seed-demo
```

Compose creates the database and app user. `init-db` ensures the tables exist and prints `MySQL tables are ready.` The optional `seed-demo` command adds the 12 sample listings across all five device categories. It can be run again after an update to add missing samples while preserving existing records and listing statuses.

### 4. Create an admin account and start the app

The prepared Cloud workspace has an admin account already. Its login is stored in the private `.preview-admin` file. For a fresh setup, run the command below and enter a name, an email address, and a password from 8 to 128 characters.

```sh
.venv/bin/flask --app retech create-admin
```

Start the server in its own terminal.

```sh
.venv/bin/waitress-serve --listen=0.0.0.0:8010 --call retech:create_app
```

Open `http://127.0.0.1:8010` in the browser on the Cloud machine, or use your workspace's port preview for `8010` when available. Log in with the admin account to see the **Admin** tab. Use **Create an account** on the login page to register an individual or recycling partner.

## Database setup and checks

MySQL uses the `mysql-data` Docker volume. A database service restart keeps the records in the volume. The schema is maintained in [retech/schema.sql](retech/schema.sql).

| Table | Records |
| --- | --- |
| `users` | Name, unique email, password hash, and account role |
| `listings` | Seller, title, category, condition, description, estimate, and availability |
| `buyback_requests` | Listing, buyer, request type, estimate at submission or exchange details, and request status |
| `transactions` | One row per completed request, with its amount and completion time |

Check the database health, version, table names, and sample count from the project directory.

```sh
docker compose ps db
docker compose exec -T db sh -c 'MYSQL_PWD="$MYSQL_PASSWORD" mysql -u"$MYSQL_USER" "$MYSQL_DATABASE"' <<'SQL'
SELECT VERSION();
SHOW TABLES;
SELECT COUNT(*) AS sample_listings
FROM listings JOIN users ON users.id = listings.seller_id
WHERE users.email = 'demo-listings@retech.example';
SQL
```

The four tables should appear. After seeding, `sample_listings` should be `12`. To check persistence, run `docker compose restart db`, wait with `docker compose up -d --wait db`, and repeat the query.

To use an existing MySQL server, create an empty database and an app user with permission to create and use tables in that database. Set `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DATABASE`, `MYSQL_USER`, and `MYSQL_PASSWORD` in `.env`. Run `init-db`, then start Waitress.

## Price estimates and request status

| Category | Base value |
| --- | ---: |
| Phones | ₹6,500 |
| Laptops | ₹12,000 |
| Chargers | ₹600 |
| Batteries | ₹450 |
| Other electronics | ₹1,800 |

The condition percentages are **Excellent** 100%, **Good** 75%, **Fair** 45%, and **Non-working** 15%.
The estimate is the category base value multiplied by the selected condition percentage, rounded down to a whole rupee. A laptop in good condition is estimated at ₹9,000. A buyback request records the estimate shown when the buyer sends it. An exchange request records the item offered in return.

A new request is **Pending**. The seller can decline it or accept it and reserve the device. Accepting one request declines competing requests. Either participant can cancel an accepted request to make the device available again. The seller can mark an accepted request complete after the handoff. This marks the device sold and adds a record to both participants' history.

## Test in the browser

Use two separate browser sessions so the seller and buyer can stay signed in at the same time. A normal window and a private window work for this.

1. **Registration and login.** Register a seller as an **Individual** and a buyer as a **Recycling partner**. Use different email addresses. Log out and log in again. Try a wrong password and confirm the form displays an error.
2. **Estimate and listing.** As the seller, open **List a device**. Enter a title and description, pick **Laptops** and **Good**, and check for ₹9,000. Publish the listing. Check that it appears in **My listings**, then edit its description.
3. **Marketplace.** As the buyer, open **Marketplace**, search for the seller's title, and filter by **Laptops** and **Good**. Confirm the device appears. Switch to **Phones** and confirm it is filtered out. Clear the filters and try the homepage category links. The seeded entries are labelled **Sample listing** for browsing.
4. **Buyback.** Open the seller's device, leave **Request type** set to **Buyback**, and send the request. Check for **Pending** in the buyer's **Requests**. In the seller's **Requests**, accept it and check for **Accepted**, the buyer's contact email, and a **Reserved** status on the listing.
5. **Completion and history.** As the seller, click **Mark complete** after the simulated handoff. Confirm the listing becomes **Sold**, disappears from the available marketplace, and appears in **Buyback history** for both accounts with the same amount.
6. **Exchange and cancellation.** Publish a second device from the seller account. In the buyer account, select **Offer an exchange** and describe the item offered. Accept it from the seller account, then cancel it from the buyer account. The listing should become **Available** again. Send another exchange request, accept it, and complete it. The history should show the exchange description.
7. **Admin and archiving.** Publish a disposable test listing, log in as admin, and open **Admin**. Check the totals, listings, and requests, then archive the disposable listing. Confirm it disappears from the marketplace. A regular account should receive a forbidden response at `/admin`.
8. **Responsive layout.** Check the home page, marketplace, listing details, and listing form at desktop and phone widths. Confirm the cards and form controls fit, photos load, and navigation links can be used with a keyboard or on a touchscreen.

## Run the automated integration suite

The suite uses a real MySQL database separate from the preview data. Create `retech_test` and grant the app database user access. The grant below assumes the default `MYSQL_USER=retech`.

```sh
docker compose exec -T db sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot' <<'SQL'
CREATE DATABASE IF NOT EXISTS retech_test CHARACTER SET utf8mb4;
GRANT ALL ON retech_test.* TO 'retech'@'%';
SQL

RETECH_TEST_DATABASE=retech_test .venv/bin/python -m unittest discover -s tests -v
```

The test runner requires a database name ending in `_test` and initializes the test tables itself. It covers authentication and form protection, listing validation and filters, server-side estimates, the buyback and exchange flows, history visibility, admin permissions, competing accepts, and re-running the demo seed. A successful run ends in `OK`.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| The preview does not open | Check the Waitress terminal and run `curl -fsS http://127.0.0.1:8010/ -o /dev/null` on the Cloud machine. Use the Cloud browser or port preview to open it. |
| MySQL connection refused | Check `docker compose ps db` and `docker compose logs --tail=50 db`. Wait for the service to become healthy before running `init-db`. |
| MySQL access denied | Confirm that the values in `.env` match the users created for the existing database. MySQL's initial Compose credentials are applied when its volume is first created. |
| Port 3306 already in use | Choose an unused `MYSQL_PORT` in `.env`, then run `docker compose up -d --wait db`. Flask reads the same port. |
| The admin tab is missing | Sign in with the account created by `create-admin` or the prepared Cloud admin account. |
| The marketplace is empty | Run `seed-demo` after `init-db`, or publish a listing from a regular account. |
| Session or form resets in the HTTP preview | Use `RETECH_SECURE_COOKIE=0` for the local HTTP URL. If the secret was changed, reopen the form or sign in again. |

## Project layout and credits

- `retech/views.py` contains the Flask routes and request transitions.
- `retech/db.py` contains the MySQL connection and setup commands. `retech/catalog.py` defines categories, conditions, and estimates. `retech/demo.py` defines the sample marketplace.
- `retech/templates/` and `retech/static/` contain the browser UI, styles, JavaScript, and images. `tests/test_marketplace.py` contains the integration suite.
- Device images are reference photos from Wikimedia Commons, served as local WebP files. See [photo sources, credits, and licenses](retech/static/images/credits.txt). The website also links to the credit file in its footer.
