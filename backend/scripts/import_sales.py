"""Import a REAL sales dataset (CSV/XLSX) into the ResiliChain database.

Built for the UCI Online Retail dataset (https://archive.ics.uci.edu/dataset/352,
CC BY 4.0 — real UK e-commerce transactions, Dec 2010 – Dec 2011) but accepts
any file with these columns (case-insensitive):

    InvoiceNo | StockCode | Description | Quantity | InvoiceDate | UnitPrice | Country

Usage (from backend/, venv active)::

    python -m scripts.import_sales "data/Online Retail.xlsx" --reset
    python -m scripts.import_sales mydata.csv --top 300 --min-days 120
    python -m scripts.import_sales mydata.csv --no-shift   # keep original dates

What it creates
---------------
- one Warehouse ("Main Fulfilment Centre") — the forecast API requires one
- one RetailStore per top country (real dimension of the data) + an "Other"
  bucket, all served by that warehouse
- Products from StockCodes (name = most frequent description, price = median
  observed unit price; unit_cost stays 0 — the dataset has no cost data and
  nothing is fabricated)
- SalesHistory = SUM(quantity) per (product, store-country, day); revenue =
  SUM(quantity x unit price) — real revenue

Cleaning (standard for this dataset, every step reported):
- cancelled invoices (InvoiceNo starting with "C") removed
- remaining rows with Quantity <= 0 or UnitPrice < 0 removed (returns/errors)
- service StockCodes without digits (POST, DOT, M, BANK CHARGES...) removed

Date shifting (--shift, default ON): all dates are moved forward by a WHOLE
number of weeks so the newest sale lands in the current week. Demand values,
weekday structure and relative timing stay exactly as in the real data — only
the calendar anchor moves, so the dashboard and forecasts are usable today.
Use --no-shift to keep original 2010-2011 dates.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, insert
from sqlalchemy.orm import Session

# App models double as the schema definition (sync engine works fine here).
from app.models import Base, Product, RetailStore, SalesHistory, Warehouse
from app.models.enums import EntityStatus

BACKEND_DIR = Path(__file__).resolve().parents[1]

COLUMN_ALIASES = {
    "invoiceno": "invoice",
    "invoice": "invoice",
    "stockcode": "sku",
    "description": "name",
    "quantity": "quantity",
    "invoicedate": "date",
    "date": "date",
    "unitprice": "price",
    "price": "price",
    "country": "country",
}


def load_raw(path: Path) -> pd.DataFrame:
    print(f"Reading {path} ...")
    if path.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path)
    df.columns = [
        COLUMN_ALIASES.get(str(c).strip().lower().replace(" ", ""), str(c))
        for c in df.columns
    ]
    required = {"sku", "quantity", "date", "price"}
    missing = required - set(df.columns)
    if missing:
        raise SystemExit(f"ERROR: dataset is missing columns: {sorted(missing)}")
    if "invoice" not in df.columns:
        df["invoice"] = ""
    if "country" not in df.columns:
        df["country"] = "Unknown"
    if "name" not in df.columns:
        df["name"] = df["sku"].astype(str)
    return df


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    report: dict[str, int] = {"raw_rows": len(df)}

    cancelled = df["invoice"].astype(str).str.startswith("C")
    df = df[~cancelled]
    report["dropped_cancelled_invoices"] = int(cancelled.sum())

    bad = (pd.to_numeric(df["quantity"], errors="coerce").fillna(0) <= 0) | (
        pd.to_numeric(df["price"], errors="coerce").fillna(-1) < 0
    )
    df = df[~bad]
    report["dropped_nonpositive_qty_or_negative_price"] = int(bad.sum())

    service = ~df["sku"].astype(str).str.contains(r"\d", regex=True)
    df = df[~service]
    report["dropped_service_codes"] = int(service.sum())

    df = df.assign(
        sku=df["sku"].astype(str).str.strip(),
        name=df["name"].astype(str).str.strip(),
        country=df["country"].astype(str).str.strip(),
        quantity=pd.to_numeric(df["quantity"], errors="coerce"),
        price=pd.to_numeric(df["price"], errors="coerce"),
        date=pd.to_datetime(df["date"], errors="coerce").dt.normalize(),
    ).dropna(subset=["date", "quantity", "price"])
    report["clean_rows"] = len(df)
    return df, report


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.import_sales",
        description="Import a real sales dataset (CSV/XLSX) into the database",
    )
    parser.add_argument("path", help="dataset file (.csv/.xlsx)")
    parser.add_argument("--db", default="dev.db", help="SQLite file (default dev.db)")
    parser.add_argument(
        "--reset", action="store_true",
        help="drop and recreate ALL tables first (destructive)",
    )
    parser.add_argument(
        "--top", type=int, default=300,
        help="keep the top N products by total quantity (default 300)",
    )
    parser.add_argument(
        "--min-days", type=int, default=150,
        help="keep products sold on >= N distinct days (default 150)",
    )
    parser.add_argument(
        "--countries", type=int, default=10,
        help="create one store per top N countries (default 10)",
    )
    shift = parser.add_mutually_exclusive_group()
    shift.add_argument(
        "--shift", dest="shift", action="store_true", default=True,
        help="shift dates forward by whole weeks to end this week (default)",
    )
    shift.add_argument(
        "--no-shift", dest="shift", action="store_false",
        help="keep the dataset's original dates",
    )
    args = parser.parse_args()

    path = Path(args.path)
    if not path.is_absolute():
        path = BACKEND_DIR / path
    if not path.exists():
        raise SystemExit(f"ERROR: file not found: {path}")

    df, report = clean(load_raw(path))

    # ---- product selection: dense, high-volume series ------------------ #
    per_product = df.groupby("sku").agg(
        total_qty=("quantity", "sum"),
        days=("date", "nunique"),
    )
    keep = per_product[per_product["days"] >= args.min_days]
    keep = keep.sort_values("total_qty", ascending=False).head(args.top)
    df = df[df["sku"].isin(keep.index)]
    report["products_kept"] = len(keep)
    report["rows_after_product_filter"] = len(df)

    # ---- optional date re-anchoring (whole weeks only) ----------------- #
    shift_weeks = 0
    if args.shift:
        last = df["date"].max().date()
        shift_weeks = max(0, (date.today() - timedelta(days=2) - last).days // 7)
        df["date"] = df["date"] + pd.Timedelta(weeks=shift_weeks)
    report["date_shift_weeks"] = shift_weeks

    # ---- aggregate to daily demand per product x country --------------- #
    top_countries = (
        df.groupby("country")["quantity"].sum().nlargest(args.countries).index
    )
    df["store_country"] = df["country"].where(
        df["country"].isin(top_countries), "Other"
    )
    df["revenue"] = df["quantity"] * df["price"]
    daily = df.groupby(["sku", "store_country", "date"], as_index=False).agg(
        quantity=("quantity", "sum"), revenue=("revenue", "sum")
    )
    report["sales_rows"] = len(daily)

    # product metadata from the real data
    meta = df.groupby("sku").agg(
        name=("name", lambda s: s.mode().iat[0] if not s.mode().empty else s.iat[0]),
        unit_price=("price", "median"),
    )

    # ---- write to the database ---------------------------------------- #
    db_path = BACKEND_DIR / args.db
    engine = create_engine(f"sqlite:///{db_path}")
    if args.reset:
        print(f"Resetting ALL tables in {db_path} ...")
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        warehouse = Warehouse(
            name="Main Fulfilment Centre",
            country="United Kingdom",
            city="London",
            capacity=500_000,
            status=EntityStatus.ACTIVE,
        )
        session.add(warehouse)
        session.flush()

        stores: dict[str, RetailStore] = {}
        for country in list(top_countries) + ["Other"]:
            store = RetailStore(
                name=f"Online — {country}",
                country=country if country != "Other" else "Various",
                warehouse_id=warehouse.id,
                status=EntityStatus.ACTIVE,
            )
            session.add(store)
            stores[country] = store
        session.flush()

        products: dict[str, uuid.UUID] = {}
        for sku, row in meta.loc[keep.index].iterrows():
            product = Product(
                sku=str(sku),
                name=str(row["name"])[:255] or str(sku),
                unit_price=round(float(row["unit_price"]), 2),
                unit_cost=0.0,  # dataset has no cost data — not fabricated
                unit="unit",
            )
            session.add(product)
            products[str(sku)] = product
        session.flush()
        product_ids = {sku: p.id for sku, p in products.items()}
        store_ids = {c: s.id for c, s in stores.items()}

        rows = [
            {
                "id": uuid.uuid4(),
                "product_id": product_ids[str(r.sku)],
                "retail_store_id": store_ids[str(r.store_country)],
                "date": r.date.date(),
                "quantity_sold": int(r.quantity),
                "revenue": round(float(r.revenue), 2),
            }
            for r in daily.itertuples()
        ]
        for i in range(0, len(rows), 5000):
            session.execute(insert(SalesHistory), rows[i : i + 5000])
        session.commit()

    # ---- report -------------------------------------------------------- #
    print("\n=== Import complete ===")
    for key, value in report.items():
        print(f"  {key:<42} {value}")
    print(f"  warehouse                                  1")
    print(f"  retail stores (per country)                {len(stores)}")
    print(f"  date range in DB                           "
          f"{daily['date'].min().date()} .. {daily['date'].max().date()}")
    if shift_weeks:
        print(f"\nNOTE: dates were shifted forward by {shift_weeks} whole weeks "
              "so the data ends this week.\nDemand values and weekday patterns "
              "are the REAL dataset values; only the calendar anchor moved "
              "(--no-shift to disable).")
    print("\nNext steps:")
    print("  1. restart the API (first signup becomes admin)")
    print("  2. rm -rf ml/models ml/artifacts   # clear models trained on old data")
    print("  3. python -m ml.eda && python -m ml.train")
    return 0


if __name__ == "__main__":
    sys.exit(main())
