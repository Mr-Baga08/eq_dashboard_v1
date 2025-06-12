# File: /app/main.py
from fastapi import FastAPI
from app.config import settings
from app.api import clients, tokens, portfolio, orders

# Create FastAPI application instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
    version="1.0.0",
    description="Trading Platform API for managing client portfolios and orders"
)

# Include API routers
app.include_router(clients.router, prefix="/api/v1")
app.include_router(tokens.router, prefix="/api/v1")
app.include_router(portfolio.router, prefix="/api/v1")
app.include_router(orders.router, prefix="/api/v1")

@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {"message": "Trading Platform API"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": "1.0.0"
    }

@app.get("/api/v1/health")
async def api_health_check():
    """Comprehensive API health check."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": "1.0.0",
        "endpoints": {
            "clients": "/api/v1/admin/clients",
            "tokens": "/api/v1/tokens",
            "portfolio": "/api/v1/portfolio", 
            "orders": "/api/v1/orders"
        },
        "features": [
            "Client Management",
            "Token Search with Redis Caching",
            "Portfolio Data Integration",
            "Batch Order Execution",
            "Position Exit Management",
            "Real-time Portfolio Updates"
        ]
    }