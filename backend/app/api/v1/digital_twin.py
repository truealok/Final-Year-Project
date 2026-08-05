"""Digital twin endpoints - the supply chain network graph."""

from fastapi import APIRouter

from app.core.dependencies import CurrentUser, DigitalTwinServiceDep
from app.schemas.digital_twin import NetworkResponse

router = APIRouter()


@router.get("/network", response_model=NetworkResponse)
async def get_network(
    _user: CurrentUser, service: DigitalTwinServiceDep
) -> NetworkResponse:
    """Return the full supply chain network: nodes, edges and a summary.

    Nodes are real suppliers/factories/warehouses/stores from the database;
    risk attributes are simulated until the graph-analytics engine lands.
    """
    return await service.network()
