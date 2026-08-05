"""Report generation, listing and export endpoints."""

import uuid

from fastapi import APIRouter, Response, status

from app.core.dependencies import CurrentUser, ManagerUser, ReportServiceDep
from app.models.enums import ReportFormat
from app.schemas.common import Page
from app.schemas.report import ReportDetail, ReportGenerateRequest, ReportRead
from app.utils.pagination import Pagination

router = APIRouter()


@router.post(
    "/generate", response_model=ReportDetail, status_code=status.HTTP_201_CREATED
)
async def generate_report(
    data: ReportGenerateRequest, user: CurrentUser, service: ReportServiceDep
) -> ReportDetail:
    """Generate a forecast / simulation / inventory / risk report."""
    report = await service.generate(data, user.id)
    return ReportDetail.model_validate(report)


@router.get("", response_model=Page[ReportRead])
async def list_reports(
    _user: CurrentUser, service: ReportServiceDep, params: Pagination
) -> Page[ReportRead]:
    """List generated reports (newest first)."""
    items, total = await service.list(params)
    return Page.build(
        [ReportRead.model_validate(r) for r in items],
        total,
        params.page,
        params.size,
    )


@router.get("/{report_id}", response_model=ReportDetail)
async def get_report(
    report_id: uuid.UUID, _user: CurrentUser, service: ReportServiceDep
) -> ReportDetail:
    """Fetch a report including its full content."""
    return ReportDetail.model_validate(await service.get(report_id))


@router.get("/{report_id}/export")
async def export_report(
    report_id: uuid.UUID,
    _user: CurrentUser,
    service: ReportServiceDep,
    export_format: ReportFormat = ReportFormat.CSV,
) -> Response:
    """Download a report as CSV or PDF."""
    payload, media_type, filename = await service.export(report_id, export_format)
    return Response(
        content=payload,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: uuid.UUID, _manager: ManagerUser, service: ReportServiceDep
) -> None:
    """Delete a report (admin / supply chain manager)."""
    await service.delete(report_id)
