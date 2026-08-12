"""Seed the CONFIGURED supply-chain network around the real demand data.

PROVENANCE — read this first
----------------------------
The UCI Online Retail dataset contains **real demand** (products, daily
sales, country of sale) but NO supplier/factory/warehouse network. This
script therefore creates a clearly-labelled, **configurable operational
network** (suppliers, factories, regional warehouses, transport routes,
inventory positions) and connects it to the REAL demand side:

- retail stores  = the country-level stores created by ``import_sales``
  (their sales rows are real dataset transactions) — left untouched;
- store→warehouse assignment, warehouse/factory/supplier entities, route
  parameters (lead time, cost, mode, reliability) = CONFIGURED values,
  deterministic (fixed seed), editable below or via the API;
- inventory quantities = derived from each warehouse's **real average daily
  demand** (cover-days policy), so stock levels are proportional to real
  demand — but they are still configured operational parameters, not
  observed stock.

Never present the network itself as observed UCI data.

Usage (from backend/, venv active)::

    python -m scripts.seed_network            # adds network (idempotent-ish)
    python -m scripts.seed_network --reset    # wipe network tables first
                                              # (products/sales/users untouched)
"""

from __future__ import annotations

import argparse
import random
import sys
import uuid
from collections import defaultdict
from pathlib import Path

from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.orm import Session

from app.models import (
    Base,
    Factory,
    Inventory,
    Product,
    RetailStore,
    SalesHistory,
    Supplier,
    TransportRoute,
    Warehouse,
)
from app.models.enums import (
    EntityStatus,
    InventoryStatus,
    NodeType,
    RiskLevel,
    TransportMode,
)

BACKEND_DIR = Path(__file__).resolve().parents[1]
SEED = 20260813  # deterministic network configuration

# ----------------------------------------------------------------- config
SUPPLIERS = [
    # name, country, city, reliability (0-100), lead_time_days, risk
    ("Shenzhen Components Ltd", "China", "Shenzhen", 88.0, 18, RiskLevel.MEDIUM),
    ("Ningbo Homeware Co", "China", "Ningbo", 82.0, 21, RiskLevel.MEDIUM),
    ("Mumbai Textiles Pvt", "India", "Mumbai", 79.0, 16, RiskLevel.HIGH),
    ("Istanbul Ceramics AS", "Turkey", "Istanbul", 85.0, 10, RiskLevel.MEDIUM),
    ("Porto Paper Works", "Portugal", "Porto", 93.0, 6, RiskLevel.LOW),
    ("Lodz Packaging Sp", "Poland", "Lodz", 91.0, 5, RiskLevel.LOW),
    ("Rhine Metals GmbH", "Germany", "Duisburg", 95.0, 4, RiskLevel.LOW),
    ("Lyon Decor SARL", "France", "Lyon", 90.0, 5, RiskLevel.LOW),
    ("Milan Glassworks SpA", "Italy", "Milan", 87.0, 7, RiskLevel.MEDIUM),
    ("Sheffield Tooling Ltd", "United Kingdom", "Sheffield", 96.0, 3, RiskLevel.LOW),
]

FACTORIES = [
    # name, country, city, capacity_per_day (units)
    ("Birmingham Assembly Plant", "United Kingdom", "Birmingham", 26_000),
    ("Leeds Finishing Works", "United Kingdom", "Leeds", 18_000),
    ("Rotterdam Processing BV", "Netherlands", "Rotterdam", 22_000),
    ("Hamburg Kitting GmbH", "Germany", "Hamburg", 15_000),
    ("Dublin Print & Pack", "EIRE", "Dublin", 9_000),
]

# 9 regional warehouses in addition to the importer's Main Fulfilment Centre.
EXTRA_WAREHOUSES = [
    # name, country, city, capacity(units)
    ("London Central DC", "United Kingdom", "London", 220_000),
    ("Manchester North DC", "United Kingdom", "Manchester", 160_000),
    ("Bristol South DC", "United Kingdom", "Bristol", 120_000),
    ("Paris Regional DC", "France", "Paris", 90_000),
    ("Frankfurt Regional DC", "Germany", "Frankfurt", 90_000),
    ("Amsterdam Regional DC", "Netherlands", "Amsterdam", 80_000),
    ("Dublin Regional DC", "EIRE", "Dublin", 60_000),
    ("Madrid Regional DC", "Spain", "Madrid", 55_000),
    ("Zurich Regional DC", "Switzerland", "Zurich", 45_000),
]

# Country stores are routed to the nearest configured regional warehouse;
# anything unlisted falls back to the Main Fulfilment Centre.
STORE_WAREHOUSE_MAP = {
    "United Kingdom": "London Central DC",
    "France": "Paris Regional DC",
    "Germany": "Frankfurt Regional DC",
    "Netherlands": "Amsterdam Regional DC",
    "EIRE": "Dublin Regional DC",
    "Spain": "Madrid Regional DC",
    "Switzerland": "Zurich Regional DC",
    "Belgium": "Amsterdam Regional DC",
    "Portugal": "Madrid Regional DC",
    "Australia": None,  # served from Main Fulfilment Centre
}

INVENTORY_COVER_DAYS = (7, 21)   # uniform range per product (deterministic rng)
DEMAND_WINDOW_DAYS = 90          # real-demand window used to size inventory


def _route(
    origin_type: NodeType,
    origin_id: uuid.UUID,
    dest_type: NodeType,
    dest_id: uuid.UUID,
    name: str,
    mode: TransportMode,
    distance_km: float,
    transit_hours: float,
    cost: float,
    risk: RiskLevel,
) -> TransportRoute:
    return TransportRoute(
        name=name,
        origin_type=origin_type,
        origin_id=origin_id,
        destination_type=dest_type,
        destination_id=dest_id,
        transport_mode=mode,
        distance_km=distance_km,
        transit_time_hours=transit_hours,
        cost_per_shipment=cost,
        status=EntityStatus.ACTIVE,
        risk_level=risk,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.seed_network",
        description="Create the configured supply-chain network "
        "(suppliers/factories/warehouses/routes/inventory)",
    )
    parser.add_argument("--db", default="dev.db")
    parser.add_argument(
        "--reset", action="store_true",
        help="delete existing network rows first (keeps products/sales/users)",
    )
    args = parser.parse_args()

    rng = random.Random(SEED)
    engine = create_engine(f"sqlite:///{BACKEND_DIR / args.db}")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        if args.reset:
            print("Removing existing network rows "
                  "(inventory, routes, suppliers, factories, extra warehouses)...")
            session.execute(delete(Inventory))
            session.execute(delete(TransportRoute))
            session.execute(delete(Factory))
            session.execute(delete(Supplier))
            # extra warehouses only — keep the importer's Main Fulfilment Centre
            main_wh = session.scalar(
                select(Warehouse).where(Warehouse.name == "Main Fulfilment Centre")
            )
            for wh in session.scalars(select(Warehouse)).all():
                if main_wh is None or wh.id != main_wh.id:
                    session.delete(wh)
            session.flush()

        # ---------------- real demand statistics (from sales) ----------- #
        last_date = session.scalar(select(func.max(SalesHistory.date)))
        if last_date is None:
            print("ERROR: no sales in the database — run scripts.import_sales "
                  "first.", file=sys.stderr)
            return 1
        window_start = last_date - __import__("datetime").timedelta(
            days=DEMAND_WINDOW_DAYS
        )
        demand_rows = session.execute(
            select(
                SalesHistory.product_id,
                SalesHistory.retail_store_id,
                func.sum(SalesHistory.quantity_sold),
            )
            .where(SalesHistory.date > window_start)
            .group_by(SalesHistory.product_id, SalesHistory.retail_store_id)
        ).all()

        stores = session.scalars(select(RetailStore)).all()
        store_by_id = {s.id: s for s in stores}
        products = session.scalars(select(Product)).all()

        # ---------------- suppliers / factories -------------------------- #
        suppliers: list[Supplier] = []
        for name, country, city, reliability, lead, risk in SUPPLIERS:
            supplier = Supplier(
                name=name, country=country, city=city,
                reliability_score=reliability, lead_time_days=lead,
                risk_level=risk, status=EntityStatus.ACTIVE,
            )
            session.add(supplier)
            suppliers.append(supplier)
        session.flush()

        factories: list[Factory] = []
        for index, (name, country, city, capacity) in enumerate(FACTORIES):
            factory = Factory(
                name=name, country=country, city=city,
                capacity_per_day=capacity,
                supplier_id=suppliers[index % len(suppliers)].id,
                status=EntityStatus.ACTIVE,
            )
            session.add(factory)
            factories.append(factory)
        session.flush()

        # ---------------- warehouses ------------------------------------- #
        main_wh = session.scalar(
            select(Warehouse).where(Warehouse.name == "Main Fulfilment Centre")
        )
        warehouses: dict[str, Warehouse] = {}
        if main_wh is not None:
            warehouses[main_wh.name] = main_wh
        for name, country, city, capacity in EXTRA_WAREHOUSES:
            existing = session.scalar(
                select(Warehouse).where(Warehouse.name == name)
            )
            if existing is None:
                existing = Warehouse(
                    name=name, country=country, city=city, capacity=capacity,
                    factory_id=factories[len(warehouses) % len(factories)].id,
                    status=EntityStatus.ACTIVE,
                )
                session.add(existing)
            warehouses[name] = existing
        session.flush()

        # ---------------- store -> warehouse assignment ------------------ #
        for store in stores:
            target_name = STORE_WAREHOUSE_MAP.get(store.country)
            wh = warehouses.get(target_name) if target_name else None
            store.warehouse_id = (wh or main_wh or list(warehouses.values())[0]).id
        session.flush()

        # ---------------- routes ----------------------------------------- #
        routes: list[TransportRoute] = []
        # supplier -> factory (each factory gets its primary + one backup;
        # 2*f_index / 2*f_index+1 covers all 10 suppliers across 5 factories)
        for f_index, factory in enumerate(factories):
            for offset in (2 * f_index, 2 * f_index + 1):
                supplier = suppliers[offset % len(suppliers)]
                overseas = supplier.lead_time_days >= 10
                routes.append(_route(
                    NodeType.SUPPLIER, supplier.id,
                    NodeType.FACTORY, factory.id,
                    f"{supplier.name} → {factory.name}",
                    TransportMode.SHIP if overseas else TransportMode.TRUCK,
                    distance_km=rng.uniform(7000, 11000) if overseas
                    else rng.uniform(300, 1500),
                    transit_hours=supplier.lead_time_days * 24,
                    cost=rng.uniform(2500, 6000) if overseas
                    else rng.uniform(400, 1400),
                    risk=supplier.risk_level,
                ))
        # factory -> warehouse (each warehouse fed by its factory + backup)
        for w_index, wh in enumerate(warehouses.values()):
            for offset in (0, 2):
                factory = factories[(w_index + offset) % len(factories)]
                cross_border = factory.country != wh.country
                routes.append(_route(
                    NodeType.FACTORY, factory.id,
                    NodeType.WAREHOUSE, wh.id,
                    f"{factory.name} → {wh.name}",
                    TransportMode.RAIL if cross_border else TransportMode.TRUCK,
                    distance_km=rng.uniform(500, 1200) if cross_border
                    else rng.uniform(80, 400),
                    transit_hours=rng.uniform(48, 96) if cross_border
                    else rng.uniform(12, 36),
                    cost=rng.uniform(700, 1800) if cross_border
                    else rng.uniform(250, 700),
                    risk=RiskLevel.MEDIUM if cross_border else RiskLevel.LOW,
                ))
        # warehouse -> retail store (from the real store assignment)
        for store in stores:
            if store.warehouse_id is None:
                continue
            wh = next(
                (w for w in warehouses.values() if w.id == store.warehouse_id),
                None,
            )
            domestic = wh is not None and wh.country == store.country
            routes.append(_route(
                NodeType.WAREHOUSE, store.warehouse_id,
                NodeType.RETAIL_STORE, store.id,
                f"{(wh.name if wh else 'Warehouse')} → {store.name}",
                TransportMode.TRUCK if domestic else TransportMode.AIR
                if store.country in ("Australia", "Various")
                else TransportMode.TRUCK,
                distance_km=rng.uniform(30, 250) if domestic
                else rng.uniform(400, 1600),
                transit_hours=rng.uniform(4, 24) if domestic
                else rng.uniform(24, 72),
                cost=rng.uniform(80, 300) if domestic else rng.uniform(200, 900),
                risk=RiskLevel.LOW if domestic else RiskLevel.MEDIUM,
            ))
        session.add_all(routes)

        # ---------------- inventory sized from REAL demand ---------------- #
        # warehouse daily demand per product = sum over its stores of the
        # store's real sales in the window / window length
        wh_product_daily: dict[tuple[uuid.UUID, uuid.UUID], float] = defaultdict(float)
        for product_id, store_id, qty in demand_rows:
            store = store_by_id.get(store_id)
            if store is None or store.warehouse_id is None:
                continue
            wh_product_daily[(store.warehouse_id, product_id)] += (
                float(qty) / DEMAND_WINDOW_DAYS
            )

        product_by_id = {p.id: p for p in products}
        inventory_rows: list[Inventory] = []
        for (wh_id, product_id), daily in wh_product_daily.items():
            if daily <= 0:
                continue
            product = product_by_id.get(product_id)
            cover = rng.uniform(*INVENTORY_COVER_DAYS)
            quantity = max(0, round(daily * cover))
            reorder = max(1, round(daily * 10))       # ~10 days of cover
            safety = max(1, round(daily * 5))         # ~5 days of cover
            if quantity <= 0:
                status = InventoryStatus.OUT_OF_STOCK
            elif quantity <= reorder:
                status = InventoryStatus.LOW_STOCK
            else:
                status = InventoryStatus.IN_STOCK
            inventory_rows.append(Inventory(
                product_id=product_id,
                warehouse_id=wh_id,
                quantity=quantity,
                reorder_point=reorder,
                safety_stock=safety,
                unit_cost=round((product.unit_price if product else 0.0) * 0.6, 2),
                status=status,
            ))
        session.add_all(inventory_rows)
        session.commit()

        # ---------------- report ----------------------------------------- #
        print("\n=== Configured network created ===")
        print(f"  suppliers          {len(suppliers)}")
        print(f"  factories          {len(factories)}")
        print(f"  warehouses         {len(warehouses)} "
              f"(incl. Main Fulfilment Centre)")
        print(f"  retail stores      {len(stores)} (REAL demand, reassigned "
              "to regional warehouses)")
        print(f"  transport routes   {len(routes)}")
        print(f"  inventory rows     {len(inventory_rows)} "
              f"(sized from real {DEMAND_WINDOW_DAYS}-day demand, "
              f"{INVENTORY_COVER_DAYS[0]}-{INVENTORY_COVER_DAYS[1]} cover days)")
        print("\nPROVENANCE: network entities/parameters are CONFIGURED "
              "(deterministic seed), demand & products are the REAL UCI dataset.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
