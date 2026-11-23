# RETECH

RETECH is an e-waste buyback marketplace built with HTML, CSS, JavaScript, Flask and MySQL. Individuals and recycling partners can list electronics, get a category-and-condition estimate in INR, and send buyback or exchange requests. When a seller accepts a request, the listing is reserved and the participants can arrange a handoff by email. The seller records the completed handoff and both participants can see it in their history.

## Start the project

Use Python 3.12+ and Docker Compose. Run these commands in the project directory in a Cloud terminal.

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt

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

docker compose up -d --wait db
.venv/bin/flask --app retech init-db
.venv/bin/waitress-serve --listen=0.0.0.0:8010 --call retech:create_app
```

Open `http://127.0.0.1:8010` in the Cloud browser. To use an existing MySQL instance, provision an empty database and an app user with permission to create and use its tables. Set the `MYSQL_*` connection settings in `.env`, then run `init-db` and start Waitress. Set `RETECH_SECURE_COOKIE=1` when serving the app over HTTPS.

## Database and admin

- Docker Compose provisions MySQL 8.4, database `retech`, app user `retech` and local port `3306` by default. MySQL stores its data in the named volume `mysql-data` across restarts.
- [retech/schema.sql](retech/schema.sql) creates `users`, `listings`, `buyback_requests` and `transactions`. The app stores password hashes. Each completed request has one transaction, with the agreed buyback amount or the exchange details recorded with its request.
- Run `.venv/bin/flask --app retech create-admin` to enter an admin name, email and password. Log in with that account and open **Admin** to review listings and requests, see totals and archive available listings.
- Run `.venv/bin/flask --app retech seed-demo` to add four sample listings. To exercise a full handoff, register two accounts and publish a listing from one of them.

## Run the integration tests

Provision a dedicated MySQL database such as `retech_test` and grant the configured app user access. With the included Compose service and the default app username:

```sh
docker compose exec -T db sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot' <<'SQL'
CREATE DATABASE IF NOT EXISTS retech_test CHARACTER SET utf8mb4;
GRANT ALL ON retech_test.* TO 'retech'@'%';
SQL

RETECH_TEST_DATABASE=retech_test .venv/bin/python -m unittest discover -s tests -v
```
