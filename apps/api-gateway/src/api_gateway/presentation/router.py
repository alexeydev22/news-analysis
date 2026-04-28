from api_gateway.application.ports import VersionProvider
from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1")


@router.get("/version")
@inject
async def version(version_provider: FromDishka[VersionProvider]) -> dict[str, str]:
    return {"service": "api-gateway", "version": version_provider.get_version()}
