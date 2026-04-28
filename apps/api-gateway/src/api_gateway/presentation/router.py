from fastapi import APIRouter

router = APIRouter(prefix="/api/v1")


@router.get("/version")
async def version() -> dict[str, str]:
    return {"service": "api-gateway", "version": "0.1.0"}
