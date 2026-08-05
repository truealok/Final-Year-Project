"""Seed the database with realistic enterprise mock data.

Usage (from the backend/ directory, with the virtualenv active):

    python -m scripts.seed            # seed (skips if data already present)
    python -m scripts.seed --reset    # drop all tables, recreate, reseed

Seeds: 3 users (admin / manager / analyst), 8 categories, 50 products,
20 suppliers, 5 factories, 10 warehouses, 15 retail stores, transport
routes, inventory, 365 days of sales history, forecast runs, simulation
runs, alerts, recommendations and settings.
"""

import argparse
import asyncio
import math
import os
import random
import sys
import uuid
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func, select  # noqa: E402

from app.core.database import async_session_factory, engine  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models import (  # noqa: E402
    Alert,
    AlertSeverity,
    Base,
    Category,
    EntityStatus,
    Factory,
    ForecastHistory,
    Inventory,
    InventoryStatus,
    NodeType,
    Product,
    Recommendation,
    RecommendationPriority,
    RecommendationStatus,
    RetailStore,
    RiskLevel,
    SalesHistory,
    Setting,
    SeverityLevel,
    SimulationHistory,
    SimulationType,
    Supplier,
    TransportMode,
    TransportRoute,
    User,
    UserRole,
    Warehouse,
)

rng = random.Random(42)

CATEGORIES = [
    ("Electronics", "Consumer and industrial electronic components"),
    ("Raw Materials", "Metals, polymers and base materials"),
    ("Automotive Parts", "Components for vehicle assembly"),
    ("Packaging", "Corrugate, film and protective packaging"),
    ("Chemicals", "Industrial and specialty chemicals"),
    ("Textiles", "Fabrics and technical textiles"),
    ("Food & Beverage", "Perishable and shelf-stable goods"),
    ("Machinery Components", "Bearings, gears and precision parts"),
]

PRODUCT_ADJECTIVES = [
    "Industrial", "Precision", "Heavy-Duty", "Compact", "Modular",
    "Standard", "Premium", "Reinforced", "Thermal", "Micro",
]
PRODUCT_NOUNS = [
    "Bearing", "Sensor Array", "Control Unit", "Valve Assembly", "Gearbox",
    "Circuit Board", "Filter Cartridge", "Actuator", "Coupling", "Relay Module",
    "Pump Core", "Battery Pack", "Display Panel", "Cable Harness", "Compressor",
]

SUPPLIER_CITIES = [
    ("Shenzhen", "China"), ("Mumbai", "India"), ("Hamburg", "Germany"),
    ("Rotterdam", "Netherlands"), ("Osaka", "Japan"), ("Busan", "South Korea"),
    ("Monterrey", "Mexico"), ("Sao Paulo", "Brazil"), ("Gdansk", "Poland"),
    ("Ho Chi Minh City", "Vietnam"), ("Istanbul", "Turkey"),
    ("Bangkok", "Thailand"), ("Taipei", "Taiwan"), ("Penang", "Malaysia"),
    ("Johannesburg", "South Africa"), ("Barcelona", "Spain"),
    ("Milan", "Italy"), ("Lyon", "France"), ("Austin", "United States"),
    ("Toronto", "Canada"),
]
SUPPLIER_SUFFIXES = ["Components", "Industries", "Materials", "Manufacturing",
                     "Supply Co", "Global"]

FACTORY_CITIES = [
    ("Stuttgart", "Germany"), ("Pune", "India"), ("Guadalajara", "Mexico"),
    ("Suzhou", "China"), ("Detroit", "United States"),
]

WAREHOUSE_CITIES = [
    ("Chicago", "United States", 41.88, -87.63),
    ("Dallas", "United States", 32.78, -96.80),
    ("Rotterdam", "Netherlands", 51.92, 4.48),
    ("Frankfurt", "Germany", 50.11, 8.68),
    ("Singapore", "Singapore", 1.35, 103.82),
    ("Dubai", "United Arab Emirates", 25.20, 55.27),
    ("Shanghai", "China", 31.23, 121.47),
    ("Mumbai", "India", 19.08, 72.88),
    ("Sydney", "Australia", -33.87, 151.21),
    ("Sao Paulo", "Brazil", -23.55, -46.63),
]

STORE_CITIES = [
    ("New York", "United States"), ("Los Angeles", "United States"),
    ("London", "United Kingdom"), ("Paris", "France"), ("Berlin", "Germany"),
    ("Tokyo", "Japan"), ("Seoul", "South Korea"), ("Delhi", "India"),
    ("Shanghai", "China"), ("Toronto", "Canada"), ("Madrid", "Spain"),
    ("Amsterdam", "Netherlands"), ("Dubai", "United Arab Emirates"),
    ("Singapore", "Singapore"), ("Melbourne", "Australia"),
]

ALERT_TEMPLATES = [
    ("Supplier reliability drop", "Reliability for {name} fell below 80%%.",
     AlertSeverity.WARNING, "supplier_monitor"),
    ("Stock below reorder point", "SKU {name} dropped below its reorder point.",
     AlertSeverity.WARNING, "inventory_monitor"),
    ("Stockout detected", "SKU {name} is out of stock at a primary warehouse.",
     AlertSeverity.CRITICAL, "inventory_monitor"),
    ("Route congestion", "Transit times on {name} increased by over 30%%.",
     AlertSeverity.WARNING, "logistics_monitor"),
    ("Severe weather warning", "Flood risk elevated near {name}.",
     AlertSeverity.CRITICAL, "risk_monitor"),
    ("Forecast run completed", "Weekly demand forecast finished for {name}.",
     AlertSeverity.INFO, "forecast_engine"),
    ("New recommendation available", "A savings opportunity was found for {name}.",
     AlertSeverity.INFO, "recommendation_engine"),
]

WEEKDAY_FACTORS = [1.05, 1.0, 0.98, 1.02, 1.15, 1.25, 0.85]


async def already_seeded() -> bool:
    async with async_session_factory() as session:
        count = await session.scalar(select(func.count(Product.id)))
        return bool(count)


async def reset_schema() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("Schema dropped and recreated.")


async def ensure_schema() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def seed() -> None:  # noqa: PLR0915 - a seed script is naturally long
    async with async_session_factory() as session:
        # ----------------------------- users --------------------------- #
        users = [
            User(email="admin@resilichain.ai", full_name="Ava Admin",
                 role=UserRole.ADMIN,
                 hashed_password=hash_password("Admin@123")),
            User(email="manager@resilichain.ai", full_name="Manu Manager",
                 role=UserRole.SUPPLY_CHAIN_MANAGER,
                 hashed_password=hash_password("Manager@123")),
            User(email="analyst@resilichain.ai", full_name="Ana Analyst",
                 role=UserRole.ANALYST,
                 hashed_password=hash_password("Analyst@123")),
        ]
        session.add_all(users)

        # --------------------------- categories ------------------------ #
        categories = [Category(name=n, description=d) for n, d in CATEGORIES]
        session.add_all(categories)
        await session.flush()

        # ---------------------------- products ------------------------- #
        products: list[Product] = []
        for i in range(50):
            adjective = rng.choice(PRODUCT_ADJECTIVES)
            noun = rng.choice(PRODUCT_NOUNS)
            unit_cost = round(rng.uniform(4, 480), 2)
            products.append(
                Product(
                    sku=f"SKU-{1000 + i}",
                    name=f"{adjective} {noun} {rng.randint(100, 999)}",
                    description=f"{adjective} grade {noun.lower()} for "
                                "enterprise supply chains.",
                    category_id=rng.choice(categories).id,
                    unit_cost=unit_cost,
                    unit_price=round(unit_cost * rng.uniform(1.25, 1.9), 2),
                )
            )
        session.add_all(products)

        # ---------------------------- suppliers ------------------------ #
        suppliers: list[Supplier] = []
        for i, (city, country) in enumerate(SUPPLIER_CITIES[:20]):
            reliability = round(rng.uniform(62, 99), 1)
            if reliability >= 90:
                risk = RiskLevel.LOW
            elif reliability >= 80:
                risk = RiskLevel.MEDIUM
            elif reliability >= 70:
                risk = RiskLevel.HIGH
            else:
                risk = RiskLevel.CRITICAL
            suffix = rng.choice(SUPPLIER_SUFFIXES)
            suppliers.append(
                Supplier(
                    name=f"{city} {suffix}",
                    country=country,
                    city=city,
                    contact_email=(
                        f"sales{i}@{city.lower().replace(' ', '')}"
                        f"{suffix.split()[0].lower()}.com"
                    ),
                    reliability_score=reliability,
                    lead_time_days=rng.randint(3, 45),
                    risk_level=risk,
                    status=rng.choices(
                        [EntityStatus.ACTIVE, EntityStatus.DISRUPTED],
                        weights=[92, 8],
                    )[0],
                )
            )
        session.add_all(suppliers)
        await session.flush()

        # ---------------------------- factories ------------------------ #
        factories = [
            Factory(
                name=f"Plant {city}",
                country=country,
                city=city,
                capacity_per_day=rng.randint(2_000, 12_000),
                supplier_id=rng.choice(suppliers).id,
            )
            for city, country in FACTORY_CITIES
        ]
        session.add_all(factories)
        await session.flush()

        # ---------------------------- warehouses ----------------------- #
        warehouses = [
            Warehouse(
                name=f"{city} Distribution Center",
                country=country,
                city=city,
                capacity=rng.randint(80_000, 400_000),
                latitude=lat,
                longitude=lng,
                factory_id=rng.choice(factories).id,
            )
            for city, country, lat, lng in WAREHOUSE_CITIES
        ]
        session.add_all(warehouses)
        await session.flush()

        # --------------------------- retail stores --------------------- #
        stores = [
            RetailStore(
                name=f"Store {city} {i + 1:02d}",
                country=country,
                city=city,
                warehouse_id=rng.choice(warehouses).id,
            )
            for i, (city, country) in enumerate(STORE_CITIES)
        ]
        session.add_all(stores)
        await session.flush()

        # ------------------------- transport routes --------------------- #
        routes: list[TransportRoute] = []

        def make_route(origin_type, origin, dest_type, dest) -> TransportRoute:
            mode = rng.choice(list(TransportMode))
            distance = round(rng.uniform(150, 12_000), 1)
            speed = {"truck": 60, "rail": 45, "ship": 30, "air": 700}[mode.value]
            return TransportRoute(
                name=f"{origin.name} -> {dest.name}",
                origin_type=origin_type,
                origin_id=origin.id,
                destination_type=dest_type,
                destination_id=dest.id,
                transport_mode=mode,
                distance_km=distance,
                transit_time_hours=round(distance / speed + rng.uniform(2, 24), 1),
                cost_per_shipment=round(distance * rng.uniform(0.8, 2.4), 2),
                status=rng.choices(
                    [EntityStatus.ACTIVE, EntityStatus.DISRUPTED],
                    weights=[90, 10],
                )[0],
                risk_level=rng.choices(
                    list(RiskLevel), weights=[55, 28, 13, 4]
                )[0],
            )

        for factory in factories:
            supplier = next(
                (s for s in suppliers if s.id == factory.supplier_id), None
            )
            if supplier:
                routes.append(
                    make_route(NodeType.SUPPLIER, supplier,
                               NodeType.FACTORY, factory)
                )
        for warehouse in warehouses:
            factory = next(
                (f for f in factories if f.id == warehouse.factory_id), None
            )
            if factory:
                routes.append(
                    make_route(NodeType.FACTORY, factory,
                               NodeType.WAREHOUSE, warehouse)
                )
        for store in stores:
            warehouse = next(
                (w for w in warehouses if w.id == store.warehouse_id), None
            )
            if warehouse:
                routes.append(
                    make_route(NodeType.WAREHOUSE, warehouse,
                               NodeType.RETAIL_STORE, store)
                )
        session.add_all(routes)

        # ---------------------------- inventory ------------------------- #
        inventory_rows: list[Inventory] = []
        for warehouse in warehouses:
            for product in rng.sample(products, k=rng.randint(15, 25)):
                reorder = rng.randint(40, 400)
                quantity = rng.choices(
                    [0, rng.randint(1, reorder), rng.randint(reorder + 1, 8_000)],
                    weights=[5, 15, 80],
                )[0]
                if quantity <= 0:
                    status = InventoryStatus.OUT_OF_STOCK
                elif quantity <= reorder:
                    status = InventoryStatus.LOW_STOCK
                else:
                    status = InventoryStatus.IN_STOCK
                inventory_rows.append(
                    Inventory(
                        product_id=product.id,
                        warehouse_id=warehouse.id,
                        quantity=quantity,
                        reorder_point=reorder,
                        safety_stock=int(reorder * 0.5),
                        unit_cost=product.unit_cost,
                        status=status,
                    )
                )
        session.add_all(inventory_rows)

        # --------------------------- sales history ----------------------- #
        print("Generating 365 days of sales history (~18k rows)...")
        today = date.today()
        sales_rows: list[SalesHistory] = []
        for product in products:
            base = rng.uniform(20, 260)
            trend = rng.uniform(-0.05, 0.15)
            for day_offset in range(365):
                day = today - timedelta(days=365 - day_offset)
                seasonal = WEEKDAY_FACTORS[day.weekday()]
                annual = 1 + 0.15 * math.sin(
                    2 * math.pi * day.timetuple().tm_yday / 365
                )
                quantity = max(
                    0,
                    int((base + trend * day_offset) * seasonal * annual
                        + rng.gauss(0, base * 0.12)),
                )
                if quantity == 0:
                    continue
                sales_rows.append(
                    SalesHistory(
                        product_id=product.id,
                        retail_store_id=rng.choice(stores).id,
                        date=day,
                        quantity_sold=quantity,
                        revenue=round(
                            quantity * product.unit_price
                            * rng.uniform(0.92, 1.05),
                            2,
                        ),
                    )
                )
                if len(sales_rows) >= 5_000:
                    session.add_all(sales_rows)
                    await session.flush()
                    sales_rows = []
        session.add_all(sales_rows)
        await session.flush()

        # -------------------------- forecast history --------------------- #
        for _ in range(30):
            product = rng.choice(products)
            warehouse = rng.choice(warehouses)
            start = today - timedelta(days=rng.randint(0, 60))
            horizon = rng.choice([7, 14, 30])
            base = rng.uniform(50, 350)
            points = []
            for offset in range(horizon):
                day = start + timedelta(days=offset)
                predicted = round(
                    base * WEEKDAY_FACTORS[day.weekday()]
                    + rng.gauss(0, base * 0.06),
                    1,
                )
                spread = round(base * 0.14, 1)
                points.append({
                    "date": day.isoformat(),
                    "predicted_demand": predicted,
                    "lower_bound": round(max(0, predicted - spread), 1),
                    "upper_bound": round(predicted + spread, 1),
                })
            session.add(
                ForecastHistory(
                    product_id=product.id,
                    warehouse_id=warehouse.id,
                    model_used=rng.choice(["prophet", "xgboost", "lstm"]),
                    start_date=start,
                    end_date=start + timedelta(days=horizon - 1),
                    confidence_level=0.95,
                    forecast_data=points,
                    metrics={
                        "mape": round(rng.uniform(4.5, 11.5), 2),
                        "rmse": round(rng.uniform(8, 30), 2),
                        "mae": round(rng.uniform(5, 22), 2),
                    },
                )
            )

        # ------------------------- simulation history -------------------- #
        for _ in range(15):
            severity = rng.choice(list(SeverityLevel))
            weight = {"low": 0.25, "medium": 0.45,
                      "high": 0.7, "critical": 0.9}[severity.value]
            duration = rng.randint(2, 45)
            probability = round(rng.uniform(0.1, 0.95), 2)
            resilience = round(
                max(5, 100 - weight * 100 * (0.55 + 0.45 * probability)
                    - min(duration, 60) * 0.35 + rng.uniform(-3, 3)),
                1,
            )
            if resilience >= 75:
                risk = RiskLevel.LOW
            elif resilience >= 55:
                risk = RiskLevel.MEDIUM
            elif resilience >= 35:
                risk = RiskLevel.HIGH
            else:
                risk = RiskLevel.CRITICAL
            affected = rng.sample(suppliers, k=2) + [rng.choice(warehouses)]
            session.add(
                SimulationHistory(
                    simulation_type=rng.choice(list(SimulationType)),
                    severity=severity,
                    duration_days=duration,
                    probability=probability,
                    parameters={"seeded": True},
                    resilience_score=resilience,
                    expected_cost=round(
                        (25_000 + 400_000 * weight) * (0.5 + probability)
                        * (1 + duration / 30) * rng.uniform(0.9, 1.1),
                        2,
                    ),
                    recovery_time_days=round(
                        duration * (0.5 + weight * 1.4)
                        * rng.uniform(0.85, 1.15),
                        1,
                    ),
                    stockout_probability=round(
                        min(0.99, weight * (0.35 + 0.65 * probability)
                            * (1 + duration / 60)),
                        3,
                    ),
                    risk_level=risk,
                    results={
                        "affected_nodes": [
                            {"id": str(node.id), "name": node.name,
                             "impact_pct": round(rng.uniform(15, 85), 1)}
                            for node in affected
                        ],
                        "affected_routes": [],
                        "engine": "mock_engine_v1",
                    },
                )
            )

        # ------------------------------ alerts --------------------------- #
        for _ in range(20):
            title, message, severity, source = rng.choice(ALERT_TEMPLATES)
            subject = rng.choice(
                [s.name for s in suppliers]
                + [p.name for p in products]
                + [w.name for w in warehouses]
            )
            session.add(
                Alert(
                    title=title,
                    message=message.replace("%%", "%").format(name=subject),
                    severity=severity,
                    source=source,
                    is_read=rng.random() < 0.4,
                )
            )

        # -------------------------- recommendations ---------------------- #
        rec_seed = [
            ("Increase safety stock for volatile SKUs",
             "Raise safety stock 15-20% for the top 10 SKUs by volatility.",
             "Stockout probability exceeded 12% for these SKUs.", "inventory"),
            ("Switch supplier for critical components",
             "Shift 30% of volume to a secondary supplier in another region.",
             "Primary supplier reliability dropped below 80%.", "sourcing"),
            ("Use alternate rail route",
             "Reroute shipments via rail for the next 2 weeks.",
             "Port congestion increased transit times by 35%.", "logistics"),
            ("Rebalance regional inventory",
             "Transfer excess stock from low- to high-demand regions.",
             "Warehouse utilization is unbalanced (91% vs 42%).", "inventory"),
            ("Pre-position seasonal stock",
             "Build 3 extra weeks of coverage before the seasonal peak.",
             "Forecast projects a 28% seasonal demand increase.", "planning"),
            ("Qualify backup air freight partner",
             "Contract a second air freight provider for urgent lanes.",
             "Single-carrier dependency raises disruption exposure.",
             "logistics"),
        ]
        for title, action, reason, category in rec_seed * 2:
            session.add(
                Recommendation(
                    title=title,
                    suggested_action=action,
                    reason=reason,
                    priority=rng.choice(list(RecommendationPriority)),
                    confidence=round(rng.uniform(0.7, 0.97), 2),
                    estimated_savings=round(rng.uniform(15_000, 250_000), 2),
                    category=category,
                    status=rng.choices(
                        list(RecommendationStatus), weights=[70, 20, 10]
                    )[0],
                    context={"generated_by": "seed"},
                )
            )

        # ------------------------------ settings ------------------------- #
        session.add_all([
            Setting(key="forecast.default_model", value={"model": "prophet"},
                    description="Default forecasting model"),
            Setting(key="simulation.default_iterations",
                    value={"iterations": 10_000},
                    description="Monte Carlo iterations (future engine)"),
            Setting(key="alerts.retention_days", value={"days": 90},
                    description="How long alerts are kept"),
        ])

        await session.commit()

    print("Seed complete.")
    print("  Users: admin@resilichain.ai / Admin@123")
    print("         manager@resilichain.ai / Manager@123")
    print("         analyst@resilichain.ai / Analyst@123")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the ResiliChain database")
    parser.add_argument(
        "--reset", action="store_true",
        help="Drop and recreate all tables before seeding",
    )
    args = parser.parse_args()

    if args.reset:
        await reset_schema()
    else:
        await ensure_schema()
        if await already_seeded():
            print("Database already contains data - use --reset to reseed.")
            await engine.dispose()
            return

    await seed()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
