#!/usr/bin/env python3
"""Import villa quote CSV downloads into the labdb.villa_quotes table.

Usage:
  export PGPASSWORD='...'                     # never put the password in the script
  python3 import_quotes.py quote1.csv [quote2.csv ...]            # villa name taken from the file name
  python3 import_quotes.py --villa "Honeypot" quote1.csv ...     # or give the villa name explicitly
  python3 import_quotes.py --dry-run quote1.csv       # parse and show, no database needed
  python3 import_quotes.py --create-table quote1.csv  # also run the V3 and V4 SQL files first

Connection (environment variables, defaults in brackets):
  PGHOST [localhost]  PGPORT [5432]  PGDATABASE [labdb]  PGUSER [labuser]  PGPASSWORD [required]

The villa name is stored in the villa_name column, so one table holds every villa. If --villa is
omitted it is read from a file name like "honeypot-quote-orman-2027-04-09.csv" (text before "-quote-",
title-cased); a file name that does not follow that pattern needs --villa.

Re-running the same file is safe: rows are keyed on (villa_name, logged, guest_email, arrival, departure)
and are updated, not duplicated.
"""
import argparse
import csv
import os
import re
import sys
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

# CSV header -> (column, type)
COLUMNS = {
    "Logged": ("logged", "ts"), "Region": ("region", "str"),
    "First name": ("first_name", "str"), "Last name": ("last_name", "str"),
    "Guest email": ("guest_email", "str"), "Source": ("source", "str"),
    "Arrival": ("arrival", "date"), "Departure": ("departure", "date"),
    "Nights": ("nights", "int"), "Nightly rate": ("nightly_rate", "num"),
    "Villa price": ("villa_price", "num"), "Clean fee": ("clean_fee", "num"),
    "Taxes": ("taxes", "num"), "Sub total": ("sub_total", "num"),
    "Pool heat wanted": ("pool_heat_wanted", "bool"), "Pool heat cost": ("pool_heat_cost", "num"),
    "Total": ("total", "num"), "Reservation deposit": ("reservation_deposit", "num"),
    "Security deposit": ("security_deposit", "num"), "Balance due": ("balance_due", "num"),
    "Currency": ("currency", "str"),
}
KEY = ("villa_name", "logged", "guest_email", "arrival", "departure")


def convert(value, kind):
    value = (value or "").strip()
    if value == "":
        return None
    if kind == "str":
        return value
    if kind == "ts":
        return datetime.strptime(value, "%Y-%m-%d %H:%M")
    if kind == "date":
        return datetime.strptime(value, "%Y-%m-%d").date()
    if kind == "int":
        return int(value)
    if kind == "num":
        return Decimal(value.replace(",", "").replace("$", ""))
    if kind == "bool":
        return value.lower() in ("yes", "y", "true", "1")
    raise ValueError(kind)


def villa_from_filename(path):
    m = re.match(r"^(.+?)-quote-", Path(path).name, re.IGNORECASE)
    return m.group(1).replace("-", " ").replace("_", " ").title() if m else None


def read_rows(path, villa):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = [h for h in COLUMNS if h not in (reader.fieldnames or [])]
        if missing:
            sys.exit(f"{path}: missing columns {missing}")
        for n, raw in enumerate(reader, start=2):
            if not any((v or "").strip() for v in raw.values()):
                continue  # blank line
            try:
                row = {col: convert(raw[h], kind) for h, (col, kind) in COLUMNS.items()}
            except (ValueError, InvalidOperation) as e:
                sys.exit(f"{path} line {n}: {e}")
            row["villa_name"] = villa
            for k in KEY:
                if row[k] is None:
                    sys.exit(f"{path} line {n}: {k} is empty")
            row["source_file"] = Path(path).name
            yield row


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--villa", help="villa name to store (default: taken from the file name)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--create-table", action="store_true")
    args = ap.parse_args()

    rows = []
    for f in args.files:
        villa = (args.villa or villa_from_filename(f) or "").strip()
        if not villa:
            sys.exit(f"{f}: cannot tell the villa from the file name; use --villa \"Name\".")
        rows.extend(read_rows(f, villa))
    print(f"Parsed {len(rows)} row(s) from {len(args.files)} file(s).")
    if args.dry_run:
        for r in rows:
            print(r)
        return

    import psycopg  # pip install "psycopg[binary]"
    if not os.environ.get("PGPASSWORD"):
        sys.exit("Set PGPASSWORD first (export PGPASSWORD='...').")
    cols = ["villa_name"] + [c for c, _ in COLUMNS.values()] + ["source_file"]
    update = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols if c not in KEY) + ", imported_at = now()"
    sql = (f"INSERT INTO villa_quotes ({', '.join(cols)}) VALUES ({', '.join('%(' + c + ')s' for c in cols)}) "
           f"ON CONFLICT ON CONSTRAINT uq_villa_quotes DO UPDATE SET {update} RETURNING (xmax = 0) AS inserted")
    conn = psycopg.connect(
        host=os.environ.get("PGHOST", "localhost"), port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ.get("PGDATABASE", "labdb"), user=os.environ.get("PGUSER", "labuser"))
    inserted = updated = 0
    with conn:  # one transaction: all rows or none
        with conn.cursor() as cur:
            if args.create_table:
                for name in ("V3__create_villa_quotes.sql", "V4__add_villa_name_to_quotes.sql"):
                    cur.execute((Path(__file__).parent / name).read_text())
            for r in rows:
                cur.execute(sql, r)
                if cur.fetchone()[0]:
                    inserted += 1
                else:
                    updated += 1
    print(f"Done: {inserted} inserted, {updated} updated.")


if __name__ == "__main__":
    main()
