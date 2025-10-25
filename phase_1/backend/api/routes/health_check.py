from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health():
    """A simple health check endpoint."""
    return {"status": "ok"}