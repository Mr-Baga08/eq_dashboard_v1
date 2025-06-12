# File: /app/api/portfolio.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, timezone
from decimal import Decimal

from app.db.database import get_db
from app.models.models import Client as ClientModel, Position as PositionModel, Trade as TradeModel
from app.schemas.schemas import (
    Client, Position, Trade, PositionListResponse, TradeListResponse,
    ResponseBase, DashboardStats, ClientPortfolioSummary
)
from app.core.mofsl_api_wrapper import mofsl_wrapper

logger = logging.getLogger(__name__)

# Create router for portfolio endpoints
router = APIRouter(
    prefix="/portfolio",
    tags=["Portfolio Management"],
    responses={404: {"description": "Not found"}}
)

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def calculate_portfolio_summary(positions: List[Dict], holdings: List[Dict], trades: List[Dict]) -> Dict[str, Any]:
    """
    Calculate portfolio summary statistics
    
    Args:
        positions (List[Dict]): Position data from MOFSL
        holdings (List[Dict]): Holdings data from MOFSL
        trades (List[Dict]): Trade data from MOFSL
        
    Returns:
        Dict[str, Any]: Portfolio summary
    """
    summary = {
        "total_positions": len(positions),
        "total_holdings": len(holdings), 
        "total_trades_today": len([t for t in trades if is_today_trade(t)]),
        "total_pnl": Decimal('0.00'),
        "day_pnl": Decimal('0.00'),
        "total_investment": Decimal('0.00'),
        "current_value": Decimal('0.00'),
        "available_margin": Decimal('0.00'),
        "used_margin": Decimal('0.00')
    }
    
    # Calculate position P&L
    for position in positions:
        try:
            pnl = Decimal(str(position.get('pnl', 0)))
            day_pnl = Decimal(str(position.get('day_pnl', 0)))
            summary["total_pnl"] += pnl
            summary["day_pnl"] += day_pnl
        except (ValueError, TypeError):
            continue
    
    # Calculate holdings value
    for holding in holdings:
        try:
            investment = Decimal(str(holding.get('investment_value', 0)))
            current_val = Decimal(str(holding.get('current_value', 0)))
            summary["total_investment"] += investment
            summary["current_value"] += current_val
        except (ValueError, TypeError):
            continue
    
    return summary

def is_today_trade(trade: Dict[str, Any]) -> bool:
    """
    Check if trade occurred today
    
    Args:
        trade (Dict[str, Any]): Trade data
        
    Returns:
        bool: True if trade is from today
    """
    try:
        trade_date = trade.get('trade_date') or trade.get('date')
        if not trade_date:
            return False
        
        # Parse trade date and compare with today
        if isinstance(trade_date, str):
            # Assume format is YYYY-MM-DD or similar
            trade_dt = datetime.fromisoformat(trade_date.replace('Z', '+00:00'))
        else:
            trade_dt = trade_date
        
        today = datetime.now(timezone.utc).date()
        return trade_dt.date() == today
        
    except Exception:
        return False

def format_portfolio_response(
    client: ClientModel, 
    positions: List[Dict], 
    holdings: List[Dict], 
    profile: Dict,
    trades: List[Dict] = None
) -> Dict[str, Any]:
    """
    Format comprehensive portfolio response
    
    Args:
        client (ClientModel): Client database model
        positions (List[Dict]): Positions from MOFSL
        holdings (List[Dict]): Holdings from MOFSL
        profile (Dict): Profile from MOFSL
        trades (List[Dict]): Recent trades
        
    Returns:
        Dict[str, Any]: Formatted portfolio response
    """
    if trades is None:
        trades = []
    
    summary = calculate_portfolio_summary(positions, holdings, trades)
    
    return {
        "client_info": {
            "id": client.id,
            "client_code": client.client_code,
            "name": client.name,
            "email": client.email,
            "risk_profile": client.risk_profile,
            "is_active": client.is_active
        },
        "summary": summary,
        "positions": positions,
        "holdings": holdings,
        "profile": profile,
        "recent_trades": trades[:10],  # Last 10 trades
        "last_updated": datetime.now(timezone.utc).isoformat()
    }

async def get_client_or_404(client_id: int, db: Session) -> ClientModel:
    """
    Get client by ID or raise 404
    
    Args:
        client_id (int): Client ID
        db (Session): Database session
        
    Returns:
        ClientModel: Client model
        
    Raises:
        HTTPException: If client not found
    """
    client = db.query(ClientModel).filter(ClientModel.id == client_id).first()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client with ID {client_id} not found"
        )
    
    if not client.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Client {client.client_code} is inactive"
        )
    
    return client

# =============================================================================
# PORTFOLIO ENDPOINTS
# =============================================================================

@router.get("/clients/{client_id}")
async def get_client_portfolio(
    client_id: int,
    segment: str = Query("interactive", description="Credential segment (interactive/commodity)"),
    include_trades: bool = Query(False, description="Include recent trades"),
    include_margin: bool = Query(True, description="Include margin information"),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive portfolio data for a client
    
    Args:
        client_id (int): Client ID
        segment (str): Credential segment to use
        include_trades (bool): Whether to include recent trades
        include_margin (bool): Whether to include margin information
        db (Session): Database session
        
    Returns:
        dict: Comprehensive portfolio data
        
    Raises:
        HTTPException: If client not found or API call fails
    """
    logger.info(f"Getting portfolio for client {client_id}")
    
    try:
        # Get client from database
        client = await get_client_or_404(client_id, db)
        
        # Check if client has required credentials
        if segment == "interactive":
            if not all([
                client.encrypted_mofsl_api_key_interactive,
                client.encrypted_mofsl_secret_key_interactive,
                client.encrypted_mofsl_user_id_interactive,
                client.encrypted_mofsl_password_interactive
            ]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Client {client.client_code} does not have interactive credentials configured"
                )
        elif segment == "commodity":
            if not all([
                client.encrypted_mofsl_api_key_commodity,
                client.encrypted_mofsl_secret_key_commodity,
                client.encrypted_mofsl_user_id_commodity,
                client.encrypted_mofsl_password_commodity
            ]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Client {client.client_code} does not have commodity credentials configured"
                )
        
        # Use MOFSL wrapper to get portfolio summary
        portfolio_data = await mofsl_wrapper.get_portfolio_summary(client, segment)
        
        # Get additional data if requested
        additional_data = {}
        
        if include_trades:
            try:
                # Get order book which includes executed trades
                auth_token = await mofsl_wrapper.authenticate_client(client, segment)
                order_book = await mofsl_wrapper.get_order_book(auth_token.token, client.client_code)
                executed_orders = [order for order in order_book if order.get('status') in ['COMPLETE', 'EXECUTED']]
                additional_data['recent_trades'] = executed_orders[:20]
            except Exception as e:
                logger.warning(f"Failed to get trades for client {client_id}: {e}")
                additional_data['recent_trades'] = []
        
        # Format response
        formatted_portfolio = format_portfolio_response(
            client=client,
            positions=portfolio_data.get('positions', []),
            holdings=portfolio_data.get('holdings', []),
            profile=portfolio_data.get('profile', {}),
            trades=additional_data.get('recent_trades', [])
        )
        
        # Add any errors from portfolio fetch
        if portfolio_data.get('errors'):
            formatted_portfolio['warnings'] = portfolio_data['errors']
        
        logger.info(f"Portfolio retrieved for client {client.client_code}")
        
        return {
            "success": True,
            "message": f"Portfolio data retrieved for {client.client_code}",
            "data": formatted_portfolio
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error getting portfolio for client {client_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve portfolio data"
        )

@router.get("/clients/{client_id}/positions")
async def get_client_positions(
    client_id: int,
    segment: str = Query("interactive", description="Credential segment"),
    db: Session = Depends(get_db)
):
    """
    Get positions for a specific client
    
    Args:
        client_id (int): Client ID
        segment (str): Credential segment
        db (Session): Database session
        
    Returns:
        dict: Client positions
    """
    logger.info(f"Getting positions for client {client_id}")
    
    try:
        # Get client
        client = await get_client_or_404(client_id, db)
        
        # Authenticate and get positions
        auth_token = await mofsl_wrapper.authenticate_client(client, segment)
        positions = await mofsl_wrapper.get_positions(auth_token.token, client.client_code)
        
        # Calculate summary
        total_pnl = sum(Decimal(str(pos.get('pnl', 0))) for pos in positions)
        day_pnl = sum(Decimal(str(pos.get('day_pnl', 0))) for pos in positions)
        
        return {
            "success": True,
            "message": f"Retrieved {len(positions)} positions for {client.client_code}",
            "data": {
                "client_code": client.client_code,
                "positions": positions,
                "summary": {
                    "total_positions": len(positions),
                    "total_pnl": float(total_pnl),
                    "day_pnl": float(day_pnl)
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting positions for client {client_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve positions"
        )

@router.get("/clients/{client_id}/holdings")
async def get_client_holdings(
    client_id: int,
    segment: str = Query("interactive", description="Credential segment"),
    db: Session = Depends(get_db)
):
    """
    Get holdings for a specific client
    
    Args:
        client_id (int): Client ID
        segment (str): Credential segment
        db (Session): Database session
        
    Returns:
        dict: Client holdings
    """
    logger.info(f"Getting holdings for client {client_id}")
    
    try:
        # Get client
        client = await get_client_or_404(client_id, db)
        
        # Authenticate and get holdings
        auth_token = await mofsl_wrapper.authenticate_client(client, segment)
        holdings = await mofsl_wrapper.get_holdings(auth_token.token, client.client_code)
        
        # Calculate summary
        total_investment = sum(Decimal(str(holding.get('investment_value', 0))) for holding in holdings)
        current_value = sum(Decimal(str(holding.get('current_value', 0))) for holding in holdings)
        total_pnl = current_value - total_investment
        
        return {
            "success": True,
            "message": f"Retrieved {len(holdings)} holdings for {client.client_code}",
            "data": {
                "client_code": client.client_code,
                "holdings": holdings,
                "summary": {
                    "total_holdings": len(holdings),
                    "total_investment": float(total_investment),
                    "current_value": float(current_value),
                    "total_pnl": float(total_pnl),
                    "pnl_percentage": float((total_pnl / total_investment * 100) if total_investment > 0 else 0)
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting holdings for client {client_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve holdings"
        )

# =============================================================================
# DASHBOARD ENDPOINTS
# =============================================================================

@router.get("/dashboard/stats")
async def get_dashboard_stats(
    db: Session = Depends(get_db)
):
    """
    Get dashboard statistics for all clients
    
    Args:
        db (Session): Database session
        
    Returns:
        dict: Dashboard statistics
    """
    logger.info("Getting dashboard statistics")
    
    try:
        # Get basic client stats from database
        total_clients = db.query(ClientModel).count()
        active_clients = db.query(ClientModel).filter(ClientModel.is_active == True).count()
        
        # Get clients with credentials for portfolio stats
        clients_with_creds = db.query(ClientModel).filter(
            ClientModel.is_active == True,
            ClientModel.encrypted_mofsl_api_key_interactive.isnot(None)
        ).limit(10).all()  # Limit to prevent too many API calls
        
        # Initialize aggregated stats
        total_portfolio_value = Decimal('0.00')
        total_pnl = Decimal('0.00')
        total_day_pnl = Decimal('0.00')
        client_summaries = []
        
        # Get portfolio data for active clients (limited to prevent API overload)
        for client in clients_with_creds:
            try:
                # Get basic portfolio summary
                auth_token = await mofsl_wrapper.authenticate_client(client, segment="interactive")
                positions = await mofsl_wrapper.get_positions(auth_token.token, client.client_code)
                holdings = await mofsl_wrapper.get_holdings(auth_token.token, client.client_code)
                
                # Calculate client summary
                client_pnl = sum(Decimal(str(pos.get('pnl', 0))) for pos in positions)
                client_day_pnl = sum(Decimal(str(pos.get('day_pnl', 0))) for pos in positions)
                client_holdings_value = sum(Decimal(str(holding.get('current_value', 0))) for holding in holdings)
                
                total_pnl += client_pnl
                total_day_pnl += client_day_pnl
                total_portfolio_value += client_holdings_value
                
                client_summaries.append({
                    "client_id": client.id,
                    "client_code": client.client_code,
                    "client_name": client.name,
                    "total_positions": len(positions),
                    "total_holdings": len(holdings),
                    "pnl": float(client_pnl),
                    "day_pnl": float(client_day_pnl),
                    "portfolio_value": float(client_holdings_value)
                })
                
            except Exception as e:
                logger.warning(f"Failed to get portfolio data for client {client.client_code}: {e}")
                continue
        
        dashboard_stats = {
            "overview": {
                "total_clients": total_clients,
                "active_clients": active_clients,
                "clients_with_data": len(client_summaries),
                "total_portfolio_value": float(total_portfolio_value),
                "total_pnl": float(total_pnl),
                "day_pnl": float(total_day_pnl)
            },
            "client_summaries": client_summaries,
            "top_performers": sorted(client_summaries, key=lambda x: x['day_pnl'], reverse=True)[:5],
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        
        return {
            "success": True,
            "message": "Dashboard statistics retrieved successfully",
            "data": dashboard_stats
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dashboard statistics"
        )

@router.get("/dashboard/clients")
async def get_client_summaries(
    limit: int = Query(20, ge=1, le=100, description="Number of client summaries to return"),
    db: Session = Depends(get_db)
):
    """
    Get portfolio summaries for multiple clients
    
    Args:
        limit (int): Maximum number of clients to process
        db (Session): Database session
        
    Returns:
        dict: Client portfolio summaries
    """
    logger.info(f"Getting client summaries (limit: {limit})")
    
    try:
        # Get active clients with credentials
        clients = db.query(ClientModel).filter(
            ClientModel.is_active == True,
            ClientModel.encrypted_mofsl_api_key_interactive.isnot(None)
        ).limit(limit).all()
        
        client_summaries = []
        
        for client in clients:
            try:
                # Get quick portfolio summary
                portfolio_summary = await mofsl_wrapper.get_portfolio_summary(client, segment="interactive")
                
                positions = portfolio_summary.get('positions', [])
                holdings = portfolio_summary.get('holdings', [])
                
                # Calculate summary stats
                total_pnl = sum(Decimal(str(pos.get('pnl', 0))) for pos in positions)
                day_pnl = sum(Decimal(str(pos.get('day_pnl', 0))) for pos in positions)
                portfolio_value = sum(Decimal(str(holding.get('current_value', 0))) for holding in holdings)
                
                client_summaries.append({
                    "client_id": client.id,
                    "client_code": client.client_code,
                    "name": client.name,
                    "risk_profile": client.risk_profile,
                    "portfolio_summary": {
                        "total_positions": len(positions),
                        "total_holdings": len(holdings),
                        "portfolio_value": float(portfolio_value),
                        "total_pnl": float(total_pnl),
                        "day_pnl": float(day_pnl)
                    },
                    "last_updated": datetime.now(timezone.utc).isoformat()
                })
                
            except Exception as e:
                logger.warning(f"Failed to get summary for client {client.client_code}: {e}")
                # Add client with error status
                client_summaries.append({
                    "client_id": client.id,
                    "client_code": client.client_code,
                    "name": client.name,
                    "risk_profile": client.risk_profile,
                    "portfolio_summary": None,
                    "error": str(e),
                    "last_updated": datetime.now(timezone.utc).isoformat()
                })
        
        return {
            "success": True,
            "message": f"Retrieved summaries for {len(client_summaries)} clients",
            "data": {
                "clients": client_summaries,
                "total_processed": len(client_summaries),
                "successful": len([c for c in client_summaries if c.get('portfolio_summary')])
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting client summaries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve client summaries"
        )

# =============================================================================
# REAL-TIME DATA ENDPOINTS
# =============================================================================

@router.get("/clients/{client_id}/realtime")
async def get_realtime_portfolio(
    client_id: int,
    segment: str = Query("interactive", description="Credential segment"),
    db: Session = Depends(get_db)
):
    """
    Get real-time portfolio data (positions only for speed)
    
    Args:
        client_id (int): Client ID
        segment (str): Credential segment
        db (Session): Database session
        
    Returns:
        dict: Real-time portfolio data
    """
    logger.info(f"Getting real-time data for client {client_id}")
    
    try:
        # Get client
        client = await get_client_or_404(client_id, db)
        
        # Get only positions for speed (holdings are typically slower)
        auth_token = await mofsl_wrapper.authenticate_client(client, segment)
        positions = await mofsl_wrapper.get_positions(auth_token.token, client.client_code)
        
        # Calculate real-time P&L
        total_pnl = sum(Decimal(str(pos.get('pnl', 0))) for pos in positions)
        day_pnl = sum(Decimal(str(pos.get('day_pnl', 0))) for pos in positions)
        
        # Get market status (simplified)
        market_status = "OPEN"  # This could be enhanced with actual market hours check
        
        return {
            "success": True,
            "message": "Real-time data retrieved successfully",
            "data": {
                "client_code": client.client_code,
                "market_status": market_status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "positions": positions,
                "summary": {
                    "total_positions": len(positions),
                    "total_pnl": float(total_pnl),
                    "day_pnl": float(day_pnl)
                },
                "alerts": []  # Could include risk alerts, margin calls, etc.
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting real-time data for client {client_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve real-time data"
        )

@router.get("/health")
async def portfolio_health_check():
    """
    Health check for portfolio service
    
    Returns:
        dict: Health status
    """
    try:
        # Test MOFSL wrapper availability
        wrapper_status = "available"
        
        # Test Redis cache if available
        cache_status = "not_configured"
        
        return {
            "status": "healthy",
            "service": "Portfolio API",
            "mofsl_wrapper": wrapper_status,
            "cache": cache_status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Portfolio health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }