# File: /app/api/tokens.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import redis
import json
import logging
from datetime import timedelta

from app.db.database import get_db
from app.models.models import Client as ClientModel, Token as TokenModel
from app.schemas.schemas import Token, TokenResponse, TokenListResponse
from app.core.mofsl_api_wrapper import mofsl_wrapper
from app.config import settings

logger = logging.getLogger(__name__)

# Create router for token endpoints
router = APIRouter(
    prefix="/tokens",
    tags=["Token Management"],
    responses={404: {"description": "Not found"}}
)

# Redis client for caching
try:
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    redis_client.ping()  # Test connection
    logger.info("Redis connection established successfully")
except Exception as e:
    logger.warning(f"Redis connection failed: {e}. Caching will be disabled.")
    redis_client = None

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_cache_key(endpoint: str, **kwargs) -> str:
    """
    Generate cache key for Redis
    
    Args:
        endpoint (str): API endpoint name
        **kwargs: Parameters to include in cache key
        
    Returns:
        str: Cache key
    """
    params = "_".join([f"{k}:{v}" for k, v in sorted(kwargs.items()) if v is not None])
    return f"trading_platform:{endpoint}:{params}"

async def get_cached_data(cache_key: str) -> Optional[Dict[str, Any]]:
    """
    Get data from Redis cache
    
    Args:
        cache_key (str): Cache key
        
    Returns:
        Optional[Dict[str, Any]]: Cached data or None
    """
    if not redis_client:
        return None
    
    try:
        cached_data = redis_client.get(cache_key)
        if cached_data:
            logger.debug(f"Cache hit for key: {cache_key}")
            return json.loads(cached_data)
    except Exception as e:
        logger.error(f"Error getting cached data: {e}")
    
    return None

async def set_cached_data(cache_key: str, data: Dict[str, Any], expire_seconds: int = 3600) -> None:
    """
    Store data in Redis cache
    
    Args:
        cache_key (str): Cache key
        data (Dict[str, Any]): Data to cache
        expire_seconds (int): Cache expiration time in seconds
    """
    if not redis_client:
        return
    
    try:
        redis_client.setex(cache_key, expire_seconds, json.dumps(data, default=str))
        logger.debug(f"Data cached with key: {cache_key}")
    except Exception as e:
        logger.error(f"Error setting cached data: {e}")

def filter_instruments(instruments: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    """
    Filter instruments based on search query
    
    Args:
        instruments (List[Dict[str, Any]]): List of instruments from MOFSL
        query (str): Search query
        
    Returns:
        List[Dict[str, Any]]: Filtered instruments
    """
    if not query or len(query) < 2:
        return instruments[:100]  # Return first 100 if no meaningful query
    
    query_lower = query.lower()
    filtered = []
    
    for instrument in instruments:
        # Search in symbol, name, and token
        symbol = str(instrument.get('symbol', '')).lower()
        name = str(instrument.get('name', '')).lower() 
        token = str(instrument.get('token', '')).lower()
        
        if (query_lower in symbol or 
            query_lower in name or
            query_lower in token or
            symbol.startswith(query_lower)):
            filtered.append(instrument)
    
    # Sort by relevance (exact matches first, then startswith, then contains)
    def sort_key(item):
        symbol = str(item.get('symbol', '')).lower()
        if symbol == query_lower:
            return 0  # Exact match
        elif symbol.startswith(query_lower):
            return 1  # Starts with query
        else:
            return 2  # Contains query
    
    filtered.sort(key=sort_key)
    return filtered[:50]  # Return top 50 results

async def get_master_client(db: Session) -> ClientModel:
    """
    Get master/admin client for instrument search
    
    Args:
        db (Session): Database session
        
    Returns:
        ClientModel: Master client with credentials
        
    Raises:
        HTTPException: If no master client found
    """
    # Look for an active client with credentials (you might want to add a specific flag for master clients)
    master_client = db.query(ClientModel).filter(
        ClientModel.is_active == True,
        ClientModel.encrypted_mofsl_api_key_interactive.isnot(None)
    ).first()
    
    if not master_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No master client available for instrument search"
        )
    
    return master_client

# =============================================================================
# TOKEN SEARCH ENDPOINTS
# =============================================================================

@router.get("/search", response_model=TokenListResponse)
async def search_tokens(
    q: str = Query(..., min_length=1, max_length=50, description="Search query for instruments"),
    exchange: str = Query("NSE", description="Exchange to search in (NSE, BSE, MCX, NCDEX)"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    use_cache: bool = Query(True, description="Whether to use cached results"),
    db: Session = Depends(get_db)
):
    """
    Search for trading instruments/tokens
    
    Args:
        q (str): Search query (symbol, name, or token)
        exchange (str): Exchange to search in
        limit (int): Maximum number of results to return
        use_cache (bool): Whether to use cached results
        db (Session): Database session
        
    Returns:
        TokenListResponse: List of matching instruments
        
    Raises:
        HTTPException: If search fails or no master client available
    """
    logger.info(f"Searching tokens: query='{q}', exchange='{exchange}', limit={limit}")
    
    try:
        # Validate exchange
        valid_exchanges = ["NSE", "BSE", "MCX", "NCDEX", "CDS"]
        if exchange.upper() not in valid_exchanges:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid exchange. Valid exchanges: {valid_exchanges}"
            )
        
        exchange = exchange.upper()
        
        # Check cache first
        cache_key = get_cache_key("search_instruments", exchange=exchange)
        cached_instruments = None
        
        if use_cache:
            cached_instruments = await get_cached_data(cache_key)
        
        if cached_instruments:
            logger.info(f"Using cached instruments for {exchange}")
            instruments_data = cached_instruments
        else:
            # Get master client for API access
            master_client = await get_master_client(db)
            
            # Authenticate and search instruments
            auth_token = await mofsl_wrapper.authenticate_client(master_client, segment="interactive")
            instruments_data = await mofsl_wrapper.search_instruments(auth_token.token, exchange)
            
            # Cache the results for 1 hour
            if use_cache:
                await set_cached_data(cache_key, instruments_data, expire_seconds=3600)
            
            logger.info(f"Fetched {len(instruments_data)} instruments from MOFSL for {exchange}")
        
        # Filter instruments based on search query
        filtered_instruments = filter_instruments(instruments_data, q)
        
        # Limit results
        limited_results = filtered_instruments[:limit]
        
        logger.info(f"Returning {len(limited_results)} filtered results for query '{q}'")
        
        return TokenListResponse(
            success=True,
            message=f"Found {len(limited_results)} instruments matching '{q}' on {exchange}",
            data=limited_results,
            total=len(filtered_instruments),
            page=1,
            per_page=limit
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error searching tokens: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search instruments"
        )

@router.get("/exchanges", response_model=Dict[str, List[str]])
async def get_supported_exchanges():
    """
    Get list of supported exchanges
    
    Returns:
        Dict[str, List[str]]: Supported exchanges and segments
    """
    exchanges = {
        "exchanges": ["NSE", "BSE", "MCX", "NCDEX", "CDS"],
        "segments": {
            "NSE": ["EQ", "FO"],
            "BSE": ["EQ", "FO"], 
            "MCX": ["CD", "CO"],
            "NCDEX": ["CD", "CO"],
            "CDS": ["CD"]
        }
    }
    
    return exchanges

@router.post("/cache/refresh")
async def refresh_instrument_cache(
    exchange: str = Query(..., description="Exchange to refresh cache for"),
    db: Session = Depends(get_db)
):
    """
    Refresh instrument cache for an exchange
    
    Args:
        exchange (str): Exchange to refresh
        db (Session): Database session
        
    Returns:
        dict: Refresh status
        
    Raises:
        HTTPException: If refresh fails
    """
    logger.info(f"Refreshing instrument cache for {exchange}")
    
    try:
        # Validate exchange
        valid_exchanges = ["NSE", "BSE", "MCX", "NCDEX", "CDS"]
        if exchange.upper() not in valid_exchanges:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid exchange. Valid exchanges: {valid_exchanges}"
            )
        
        exchange = exchange.upper()
        
        # Get master client
        master_client = await get_master_client(db)
        
        # Fetch fresh data from MOFSL
        auth_token = await mofsl_wrapper.authenticate_client(master_client, segment="interactive")
        instruments_data = await mofsl_wrapper.search_instruments(auth_token.token, exchange)
        
        # Update cache
        cache_key = get_cache_key("search_instruments", exchange=exchange)
        await set_cached_data(cache_key, instruments_data, expire_seconds=3600)
        
        logger.info(f"Cache refreshed for {exchange}: {len(instruments_data)} instruments")
        
        return {
            "success": True,
            "message": f"Cache refreshed for {exchange}",
            "instruments_count": len(instruments_data),
            "cache_key": cache_key
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error refreshing cache for {exchange}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh cache for {exchange}"
        )

@router.get("/cache/status")
async def get_cache_status():
    """
    Get cache status for all exchanges
    
    Returns:
        dict: Cache status information
    """
    if not redis_client:
        return {
            "cache_enabled": False,
            "message": "Redis cache is not available"
        }
    
    try:
        exchanges = ["NSE", "BSE", "MCX", "NCDEX", "CDS"]
        cache_status = {}
        
        for exchange in exchanges:
            cache_key = get_cache_key("search_instruments", exchange=exchange)
            ttl = redis_client.ttl(cache_key)
            exists = redis_client.exists(cache_key)
            
            cache_status[exchange] = {
                "cached": bool(exists),
                "ttl_seconds": ttl if ttl > 0 else 0,
                "cache_key": cache_key
            }
        
        return {
            "cache_enabled": True,
            "redis_connected": True,
            "exchanges": cache_status
        }
        
    except Exception as e:
        logger.error(f"Error getting cache status: {e}")
        return {
            "cache_enabled": False,
            "error": str(e)
        }

# =============================================================================
# LOCAL DATABASE TOKEN ENDPOINTS
# =============================================================================

@router.get("/local", response_model=TokenListResponse)
async def get_local_tokens(
    skip: int = Query(0, ge=0, description="Number of tokens to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of tokens to return"),
    exchange: Optional[str] = Query(None, description="Filter by exchange"),
    segment: Optional[str] = Query(None, description="Filter by segment"),
    is_active: bool = Query(True, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by symbol or name"),
    db: Session = Depends(get_db)
):
    """
    Get tokens from local database
    
    Args:
        skip (int): Number of records to skip
        limit (int): Number of records to return
        exchange (Optional[str]): Filter by exchange
        segment (Optional[str]): Filter by segment
        is_active (bool): Filter by active status
        search (Optional[str]): Search term
        db (Session): Database session
        
    Returns:
        TokenListResponse: List of tokens from database
    """
    logger.info(f"Getting local tokens: skip={skip}, limit={limit}")
    
    try:
        # Build query
        query = db.query(TokenModel)
        
        # Apply filters
        if is_active:
            query = query.filter(TokenModel.is_active == is_active)
        
        if exchange:
            query = query.filter(TokenModel.exchange == exchange.upper())
        
        if segment:
            query = query.filter(TokenModel.segment == segment.upper())
        
        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                (TokenModel.symbol.ilike(search_filter)) |
                (TokenModel.name.ilike(search_filter)) |
                (TokenModel.token.ilike(search_filter))
            )
        
        # Get total count
        total = query.count()
        
        # Apply pagination and get results
        tokens = query.offset(skip).limit(limit).all()
        
        # Convert to response format
        token_list = []
        for token in tokens:
            token_data = Token.model_validate(token)
            token_list.append(token_data)
        
        logger.info(f"Retrieved {len(token_list)} local tokens (total: {total})")
        
        return TokenListResponse(
            success=True,
            message=f"Retrieved {len(token_list)} tokens from database",
            data=token_list,
            total=total,
            page=skip // limit + 1,
            per_page=limit
        )
        
    except Exception as e:
        logger.error(f"Error getting local tokens: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve local tokens"
        )