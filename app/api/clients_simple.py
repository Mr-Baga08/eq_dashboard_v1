# File: /app/api/clients_simple.py
# Simplified version to test basic functionality

from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)

# Create router for client endpoints
router = APIRouter(
    prefix="/admin/clients",
    tags=["Client Management"],
    responses={404: {"description": "Not found"}}
)

@router.get("/")
async def list_clients():
    """
    Simple endpoint to test basic functionality
    """
    return {
        "success": True,
        "message": "Client management endpoint working",
        "data": []
    }

@router.get("/health")
async def client_health():
    """
    Health check for client management
    """
    return {
        "status": "healthy",
        "service": "Client Management API"
    }