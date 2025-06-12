# File: /app/main_simple.py
# Simplified version to test basic FastAPI functionality

from fastapi import FastAPI

# Create FastAPI application instance
app = FastAPI(
    title="Trading Platform API",
    debug=False,
    version="1.0.0",
    description="Trading Platform API for managing client portfolios and orders"
)

@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {"message": "Trading Platform API"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Trading Platform API",
        "version": "1.0.0"
    }

@app.get("/test")
async def test_endpoint():
    """Test endpoint to verify basic functionality."""
    return {
        "status": "working",
        "message": "FastAPI is working correctly"
    }