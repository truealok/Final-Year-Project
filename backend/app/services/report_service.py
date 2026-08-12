"""Report generation and export (CSV / PDF) business logic."""

from __future__ import annotations

import csv
import io
import uuid
from datetime import date

from app.models.enums import ReportFormat, ReportType
from app.models.report import Report
from app.repositories.alert_repository import AlertRepository
from app.repositories.forecast_repository import (
    FORECAST_LOAD_OPTIONS,
    ForecastRepository,
)
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.report_repository import ReportRepository
from app.repositories.simulation_repository import SimulationRepository
from app.repositories.supplier_repository import SupplierRepository
from app.schemas.report import ReportGenerateRequest
from app.utils.exceptions import BadRequestError, NotFoundError
from app.utils.pagination import PaginationParams

_MAX_ROWS = 200


class ReportService:
    def __init__(
        self,
        reports: ReportRepository,
        forecasts: ForecastRepository,
        simulations: SimulationRepository,
        inventory: InventoryRepository,
        suppliers: SupplierRepository,
        alerts: AlertRepository,
    ) -> None:
        self.reports = reports
        self.forecasts = forecasts
        self.simulations = simulations
        self.inventory = inventory
        self.suppliers = suppliers
        self.alerts = alerts

    # ------------------------------------------------------------------ #
    # Content builders
    # ------------------------------------------------------------------ #
    async def _forecast_content(self) -> dict:
        items, _ = await self.forecasts.list(
            limit=_MAX_ROWS, options=FORECAST_LOAD_OPTIONS
        )
        rows = [
            [
                f.product.name,
                f.warehouse.name,
                f.model_used,
                str(f.start_date),
                str(f.end_date),
                f.confidence_level,
                f.metrics.get("mape", ""),
            ]
            for f in items
        ]
        return {
            "columns": [
                "Product", "Warehouse", "Model", "Start", "End",
                "Confidence", "MAPE",
            ],
            "rows": rows,
            "summary": {"total_forecasts": len(rows)},
        }

    async def _simulation_content(self) -> dict:
        items, _ = await self.simulations.list(limit=_MAX_ROWS)
        rows = [
            [
                s.simulation_type.value,
                s.severity.value,
                s.duration_days,
                s.resilience_score,
                s.expected_cost,
                s.recovery_time_days,
                s.stockout_probability,
                s.risk_level.value,
            ]
            for s in items
        ]
        avg_resilience = (
            round(sum(s.resilience_score for s in items) / len(items), 1)
            if items
            else 0.0
        )
        return {
            "columns": [
                "Type", "Severity", "Duration (days)", "Resilience",
                "Expected Cost", "Recovery (days)", "Stockout Prob", "Risk",
            ],
            "rows": rows,
            "summary": {
                "total_simulations": len(rows),
                "avg_resilience_score": avg_resilience,
            },
        }

    async def _inventory_content(self) -> dict:
        items, _ = await self.inventory.list(limit=_MAX_ROWS)
        rows = [
            [
                i.product.sku,
                i.product.name,
                i.warehouse.name,
                i.quantity,
                i.reorder_point,
                i.safety_stock,
                round(i.quantity * i.unit_cost, 2),
                i.status.value,
            ]
            for i in items
        ]
        return {
            "columns": [
                "SKU", "Product", "Warehouse", "Quantity", "Reorder Point",
                "Safety Stock", "Value", "Status",
            ],
            "rows": rows,
            "summary": await self.inventory.summary(),
        }

    async def _risk_content(self) -> dict:
        suppliers, _ = await self.suppliers.list(limit=_MAX_ROWS)
        rows = [
            [
                s.name,
                s.country,
                s.reliability_score,
                s.lead_time_days,
                s.risk_level.value,
                s.status.value,
            ]
            for s in suppliers
        ]
        return {
            "columns": [
                "Supplier", "Country", "Reliability", "Lead Time (days)",
                "Risk Level", "Status",
            ],
            "rows": rows,
            "summary": {
                "total_suppliers": len(rows),
                "alerts_by_severity": await self.alerts.severity_counts(),
            },
        }

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    async def generate(
        self, request: ReportGenerateRequest, user_id: uuid.UUID | None
    ) -> Report:
        builders = {
            ReportType.FORECAST: self._forecast_content,
            ReportType.SIMULATION: self._simulation_content,
            ReportType.INVENTORY: self._inventory_content,
            ReportType.RISK: self._risk_content,
        }
        content = await builders[request.report_type]()
        name = request.name or (
            f"{request.report_type.value.title()} Report {date.today()}"
        )
        return await self.reports.create(
            name=name,
            report_type=request.report_type,
            format=request.format,
            parameters=request.parameters,
            content=content,
            status="completed",
            created_by=user_id,
        )

    async def list(
        self, params: PaginationParams
    ) -> tuple[list[Report], int]:
        return await self.reports.list(offset=params.offset, limit=params.size)

    async def get(self, report_id: uuid.UUID) -> Report:
        report = await self.reports.get(report_id)
        if report is None:
            raise NotFoundError("Report not found.")
        return report

    async def delete(self, report_id: uuid.UUID) -> None:
        report = await self.get(report_id)
        await self.reports.delete(report)

    # ------------------------------------------------------------------ #
    # Export
    # ------------------------------------------------------------------ #
    async def export(
        self, report_id: uuid.UUID, export_format: ReportFormat
    ) -> tuple[bytes, str, str]:
        """Render a stored report. Returns ``(payload, media_type, filename)``."""
        report = await self.get(report_id)
        base_name = report.name.replace(" ", "_").lower()

        if export_format == ReportFormat.CSV:
            return (
                self._to_csv(report.content),
                "text/csv",
                f"{base_name}.csv",
            )
        if export_format == ReportFormat.PDF:
            return (
                self._to_pdf(report.name, report.content),
                "application/pdf",
                f"{base_name}.pdf",
            )
        raise BadRequestError("Unsupported export format; use csv or pdf.")

    @staticmethod
    def _to_csv(content: dict) -> bytes:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(content.get("columns", []))
        writer.writerows(content.get("rows", []))
        return buffer.getvalue().encode("utf-8-sig")

    @staticmethod
    def _to_pdf(title: str, content: dict) -> bytes:
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import (
                Paragraph,
                SimpleDocTemplate,
                Spacer,
                Table,
                TableStyle,
            )
        except ImportError as exc:  # pragma: no cover
            raise BadRequestError(
                "PDF export requires the 'reportlab' package."
            ) from exc

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), title=title)
        styles = getSampleStyleSheet()

        table_data = [content.get("columns", [])] + [
            [str(cell)[:40] for cell in row]
            for row in content.get("rows", [])[:100]
        ]
        table = Table(table_data, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                     [colors.white, colors.HexColor("#f3f4f6")]),
                ]
            )
        )
        doc.build(
            [
                Paragraph(title, styles["Title"]),
                Spacer(1, 12),
                table,
            ]
        )
        return buffer.getvalue()
