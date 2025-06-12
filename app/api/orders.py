# File: /app/api/orders.py
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
import logging
import asyncio
from datetime import datetime, timezone
from decimal import Decimal

from app.db.database import get_db
from app.models.models import Client as ClientModel, Order as OrderModel, Token as TokenModel
from app.schemas.schemas import OrderCreate, Order, OrderResponse, ResponseBase
from app.core.mofsl_api_wrapper import mofsl_wrapper

logger = logging.getLogger(__name__)

# Create router for order endpoints
router = APIRouter(
    prefix="/orders",
    tags=["Order Management"],
    responses={404: {"description": "Not found"}}
)

# =============================================================================
# REQUEST/RESPONSE SCHEMAS
# =============================================================================

class ClientOrder(BaseModel):
    """Individual client order within batch execution"""
    client_id: int = Field(..., gt=0, description="Client ID")
    quantity: int = Field(..., gt=0, description="Quantity to trade")
    price: Optional[Decimal] = Field(None, gt=0, description="Limit price (optional for market orders)")
    remarks: Optional[str] = Field(None, max_length=100, description="Order remarks")

class BatchOrderRequest(BaseModel):
    """Batch order execution request"""
    # Trade parameters
    token_id: str = Field(..., description="MOFSL token/symbol ID")
    symbol: str = Field(..., min_length=1, max_length=20, description="Trading symbol")
    exchange: str = Field(..., pattern=r'^(NSE|BSE|MCX|NCDEX)$', description="Exchange")
    order_type: str = Field(..., pattern=r'^(MKT|LMT|SLM|SL)$', description="Order type")
    transaction_type: str = Field(..., pattern=r'^(BUY|SELL)$', description="Transaction type")
    product_type: str = Field(default="MIS", pattern=r'^(MIS|CNC|NRML)$', description="Product type")
    
    # Default price for limit orders (can be overridden per client)
    default_price: Optional[Decimal] = Field(None, gt=0, description="Default price for limit orders")
    trigger_price: Optional[Decimal] = Field(None, gt=0, description="Trigger price for SL orders")
    
    # Execution parameters
    segment: str = Field(default="interactive", pattern=r'^(interactive|commodity)$', description="Credential segment")
    validity: str = Field(default="DAY", pattern=r'^(DAY|IOC|GTD)$', description="Order validity")
    
    # Client orders
    client_orders: List[ClientOrder] = Field(..., min_items=1, max_items=100, description="List of client orders")
    
    # Execution options
    dry_run: bool = Field(default=False, description="Dry run mode (validate without executing)")
    max_concurrent: int = Field(default=5, ge=1, le=20, description="Maximum concurrent order executions")

class OrderExecutionResult(BaseModel):
    """Result of individual order execution"""
    client_id: int
    client_code: str
    quantity: int
    price: Optional[Decimal]
    success: bool
    order_id: Optional[str] = None
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None

class BatchOrderResponse(BaseModel):
    """Batch order execution response"""
    success: bool
    message: str
    summary: Dict[str, Any]
    results: List[OrderExecutionResult]
    execution_metadata: Dict[str, Any]

class ExitOrderRequest(BaseModel):
    """Exit order request for specific token"""
    token_mofsl_id: str = Field(..., description="MOFSL token ID to exit")
    exchange: str = Field(..., pattern=r'^(NSE|BSE|MCX|NCDEX)$', description="Exchange")
    order_type: str = Field(default="MKT", pattern=r'^(MKT|LMT)$', description="Exit order type")
    price: Optional[Decimal] = Field(None, gt=0, description="Exit price for limit orders")
    segment: str = Field(default="interactive", description="Credential segment")
    client_filter: Optional[List[int]] = Field(None, description="Specific client IDs to exit (optional)")
    min_quantity: int = Field(default=1, ge=1, description="Minimum position quantity to exit")
    dry_run: bool = Field(default=False, description="Dry run mode")

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def get_client_with_validation(client_id: int, segment: str, db: Session) -> ClientModel:
    """
    Get client and validate credentials for trading
    
    Args:
        client_id (int): Client ID
        segment (str): Credential segment
        db (Session): Database session
        
    Returns:
        ClientModel: Validated client
        
    Raises:
        ValueError: If client not found or invalid
    """
    client = db.query(ClientModel).filter(ClientModel.id == client_id).first()
    
    if not client:
        raise ValueError(f"Client with ID {client_id} not found")
    
    if not client.is_active:
        raise ValueError(f"Client {client.client_code} is inactive")
    
    # Validate credentials
    if segment == "interactive":
        if not all([
            client.encrypted_mofsl_api_key_interactive,
            client.encrypted_mofsl_secret_key_interactive,
            client.encrypted_mofsl_user_id_interactive,
            client.encrypted_mofsl_password_interactive
        ]):
            raise ValueError(f"Client {client.client_code} does not have interactive credentials")
    elif segment == "commodity":
        if not all([
            client.encrypted_mofsl_api_key_commodity,
            client.encrypted_mofsl_secret_key_commodity,
            client.encrypted_mofsl_user_id_commodity,
            client.encrypted_mofsl_password_commodity
        ]):
            raise ValueError(f"Client {client.client_code} does not have commodity credentials")
    
    return client

def create_order_from_request(
    batch_request: BatchOrderRequest, 
    client_order: ClientOrder, 
    token_id: int
) -> OrderCreate:
    """
    Create OrderCreate object from batch request and client order
    
    Args:
        batch_request (BatchOrderRequest): Batch order parameters
        client_order (ClientOrder): Individual client order
        token_id (int): Database token ID
        
    Returns:
        OrderCreate: Order creation schema
    """
    # Use client-specific price or default price
    order_price = client_order.price or batch_request.default_price
    
    return OrderCreate(
        client_id=client_order.client_id,
        token_id=token_id,
        order_type=batch_request.order_type,
        transaction_type=batch_request.transaction_type,
        product_type=batch_request.product_type,
        quantity=client_order.quantity,
        price=order_price,
        trigger_price=batch_request.trigger_price,
        exchange=batch_request.exchange,
        validity=batch_request.validity,
        remarks=client_order.remarks or f"Batch order - {batch_request.symbol}"
    )

async def execute_single_order(
    client_id: int,
    client_order: ClientOrder,
    batch_request: BatchOrderRequest,
    token_id: int,
    db: Session
) -> OrderExecutionResult:
    """
    Execute order for a single client
    
    Args:
        client_id (int): Client ID
        client_order (ClientOrder): Client order details
        batch_request (BatchOrderRequest): Batch request parameters
        token_id (int): Database token ID
        db (Session): Database session
        
    Returns:
        OrderExecutionResult: Execution result
    """
    start_time = datetime.now()
    
    try:
        # Get and validate client
        client = await get_client_with_validation(client_id, batch_request.segment, db)
        
        # Create order object
        order_create = create_order_from_request(batch_request, client_order, token_id)
        
        if batch_request.dry_run:
            # Dry run - validate only
            return OrderExecutionResult(
                client_id=client_id,
                client_code=client.client_code,
                quantity=client_order.quantity,
                price=client_order.price or batch_request.default_price,
                success=True,
                order_id="DRY_RUN",
                execution_time_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )
        
        # Execute real order
        order_id = await mofsl_wrapper.place_order(
            auth_token="",  # Will be handled by authenticate_client
            order_details=order_create,
            client_code=client.client_code
        )
        
        # Save order to database
        db_order = OrderModel(
            order_id=order_id,
            client_id=client_id,
            token_id=token_id,
            order_type=batch_request.order_type,
            transaction_type=batch_request.transaction_type,
            product_type=batch_request.product_type,
            quantity=client_order.quantity,
            price=client_order.price or batch_request.default_price,
            trigger_price=batch_request.trigger_price,
            exchange=batch_request.exchange,
            validity=batch_request.validity,
            status="PENDING",
            remarks=client_order.remarks or f"Batch order - {batch_request.symbol}"
        )
        
        db.add(db_order)
        db.commit()
        
        execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        return OrderExecutionResult(
            client_id=client_id,
            client_code=client.client_code,
            quantity=client_order.quantity,
            price=client_order.price or batch_request.default_price,
            success=True,
            order_id=order_id,
            execution_time_ms=execution_time
        )
        
    except Exception as e:
        execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
        error_message = str(e)
        
        logger.error(f"Order execution failed for client {client_id}: {error_message}")
        
        return OrderExecutionResult(
            client_id=client_id,
            client_code=f"CLIENT_{client_id}",  # Fallback if client not found
            quantity=client_order.quantity,
            price=client_order.price or batch_request.default_price,
            success=False,
            error_message=error_message,
            execution_time_ms=execution_time
        )

async def get_client_positions_for_token(client: ClientModel, token_mofsl_id: str, segment: str) -> List[Dict]:
    """
    Get client positions for specific token
    
    Args:
        client (ClientModel): Client model
        token_mofsl_id (str): MOFSL token ID
        segment (str): Credential segment
        
    Returns:
        List[Dict]: Positions for the token
    """
    try:
        auth_token = await mofsl_wrapper.authenticate_client(client, segment)
        all_positions = await mofsl_wrapper.get_positions(auth_token.token, client.client_code)
        
        # Filter positions for specific token
        token_positions = [
            pos for pos in all_positions 
            if str(pos.get('token', '')).strip() == token_mofsl_id.strip()
        ]
        
        return token_positions
        
    except Exception as e:
        logger.error(f"Error getting positions for client {client.client_code}, token {token_mofsl_id}: {e}")
        return []

# =============================================================================
# BATCH ORDER EXECUTION ENDPOINTS
# =============================================================================

@router.post("/execute-all", response_model=BatchOrderResponse)
async def execute_batch_orders(
    request: BatchOrderRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Execute batch orders for multiple clients
    
    Args:
        request (BatchOrderRequest): Batch order request
        background_tasks (BackgroundTasks): Background task queue
        db (Session): Database session
        
    Returns:
        BatchOrderResponse: Execution results for all orders
        
    Raises:
        HTTPException: If validation fails
    """
    logger.info(f"Executing batch orders: {len(request.client_orders)} orders for {request.symbol}")
    
    execution_start = datetime.now()
    
    try:
        # Validate token exists (for database tracking)
        # Note: We use token_id as string for MOFSL API calls
        token_id = 1  # Placeholder - in real implementation, you'd map this properly
        
        # Validate order parameters
        if request.order_type in ["LMT", "SL"] and not request.default_price and not any(co.price for co in request.client_orders):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Price is required for limit orders"
            )
        
        if request.order_type in ["SLM", "SL"] and not request.trigger_price:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trigger price is required for stop-loss orders"
            )
        
        # Filter out zero quantity orders
        valid_orders = [co for co in request.client_orders if co.quantity > 0]
        
        if not valid_orders:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid orders with quantity > 0"
            )
        
        logger.info(f"Processing {len(valid_orders)} valid orders (filtered from {len(request.client_orders)})")
        
        # Execute orders with concurrency control
        semaphore = asyncio.Semaphore(request.max_concurrent)
        
        async def execute_with_semaphore(client_order: ClientOrder):
            async with semaphore:
                return await execute_single_order(
                    client_order.client_id,
                    client_order,
                    request,
                    token_id,
                    db
                )
        
        # Execute all orders concurrently
        tasks = [execute_with_semaphore(co) for co in valid_orders]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        execution_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                execution_results.append(OrderExecutionResult(
                    client_id=valid_orders[i].client_id,
                    client_code=f"CLIENT_{valid_orders[i].client_id}",
                    quantity=valid_orders[i].quantity,
                    price=valid_orders[i].price or request.default_price,
                    success=False,
                    error_message=str(result),
                    execution_time_ms=0
                ))
            else:
                execution_results.append(result)
        
        # Calculate summary
        successful_orders = [r for r in execution_results if r.success]
        failed_orders = [r for r in execution_results if not r.success]
        total_quantity = sum(r.quantity for r in successful_orders)
        avg_execution_time = sum(r.execution_time_ms or 0 for r in execution_results) / len(execution_results) if execution_results else 0
        
        total_execution_time = int((datetime.now() - execution_start).total_seconds() * 1000)
        
        summary = {
            "total_orders": len(valid_orders),
            "successful_orders": len(successful_orders),
            "failed_orders": len(failed_orders),
            "success_rate": (len(successful_orders) / len(valid_orders)) * 100 if valid_orders else 0,
            "total_quantity": int(total_quantity),
            "symbol": request.symbol,
            "transaction_type": request.transaction_type,
            "order_type": request.order_type
        }
        
        execution_metadata = {
            "execution_time_ms": total_execution_time,
            "avg_order_execution_ms": int(avg_execution_time),
            "max_concurrent": request.max_concurrent,
            "dry_run": request.dry_run,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        response = BatchOrderResponse(
            success=len(successful_orders) > 0,
            message=f"Batch execution completed: {len(successful_orders)}/{len(valid_orders)} orders successful",
            summary=summary,
            results=execution_results,
            execution_metadata=execution_metadata
        )
        
        logger.info(f"Batch execution completed: {len(successful_orders)}/{len(valid_orders)} successful")
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Batch order execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch order execution failed: {str(e)}"
        )

# =============================================================================
# TOKEN EXIT ENDPOINTS
# =============================================================================

@router.post("/tokens/{token_mofsl_id}/exit-all")
async def exit_all_positions(
    token_mofsl_id: str,
    request: ExitOrderRequest,
    db: Session = Depends(get_db)
):
    """
    Exit all positions for a specific token across multiple clients
    
    Args:
        token_mofsl_id (str): MOFSL token ID to exit
        request (ExitOrderRequest): Exit order parameters
        db (Session): Database session
        
    Returns:
        dict: Exit execution results
        
    Raises:
        HTTPException: If exit fails
    """
    logger.info(f"Exiting all positions for token {token_mofsl_id}")
    
    execution_start = datetime.now()
    
    try:
        # Get clients with active positions (or use client filter)
        if request.client_filter:
            clients = db.query(ClientModel).filter(
                ClientModel.id.in_(request.client_filter),
                ClientModel.is_active == True
            ).all()
        else:
            # Get all active clients with credentials
            clients = db.query(ClientModel).filter(
                ClientModel.is_active == True,
                ClientModel.encrypted_mofsl_api_key_interactive.isnot(None)
            ).all()
        
        if not clients:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active clients found for exit operation"
            )
        
        logger.info(f"Processing exit for {len(clients)} clients")
        
        # Get positions for each client and prepare exit orders
        exit_results = []
        clients_to_exit = []
        
        for client in clients:
            try:
                positions = await get_client_positions_for_token(client, token_mofsl_id, request.segment)
                
                # Filter positions that meet minimum quantity
                exit_positions = [
                    pos for pos in positions 
                    if abs(int(pos.get('quantity', 0))) >= request.min_quantity
                ]
                
                if exit_positions:
                    clients_to_exit.append((client, exit_positions))
                    logger.debug(f"Client {client.client_code}: {len(exit_positions)} positions to exit")
                
            except Exception as e:
                logger.warning(f"Failed to get positions for client {client.client_code}: {e}")
                exit_results.append({
                    "client_id": client.id,
                    "client_code": client.client_code,
                    "success": False,
                    "error_message": f"Failed to fetch positions: {str(e)}",
                    "positions_exited": 0
                })
        
        if not clients_to_exit:
            return {
                "success": True,
                "message": "No positions found to exit for the specified token",
                "summary": {
                    "clients_processed": len(clients),
                    "clients_with_positions": 0,
                    "total_positions_exited": 0
                },
                "results": exit_results
            }
        
        # Execute exit orders
        async def execute_client_exit(client_positions_tuple):
            client, positions = client_positions_tuple
            client_exit_count = 0
            client_errors = []
            
            try:
                auth_token = await mofsl_wrapper.authenticate_client(client, request.segment)
                
                for position in positions:
                    try:
                        current_qty = int(position.get('quantity', 0))
                        
                        if current_qty == 0:
                            continue
                        
                        # Determine exit transaction type (opposite of current position)
                        exit_transaction = "SELL" if current_qty > 0 else "BUY"
                        exit_quantity = abs(current_qty)
                        
                        if request.dry_run:
                            client_exit_count += 1
                            continue
                        
                        # Create exit order
                        exit_order = OrderCreate(
                            client_id=client.id,
                            token_id=1,  # Placeholder
                            order_type=request.order_type,
                            transaction_type=exit_transaction,
                            product_type=position.get('product_type', 'MIS'),
                            quantity=exit_quantity,
                            price=request.price,
                            exchange=request.exchange,
                            validity="DAY",
                            remarks=f"Exit order for {token_mofsl_id}"
                        )
                        
                        # Place exit order
                        order_id = await mofsl_wrapper.place_order(
                            auth_token.token,
                            exit_order,
                            client.client_code
                        )
                        
                        client_exit_count += 1
                        
                        # Save to database
                        db_order = OrderModel(
                            order_id=order_id,
                            client_id=client.id,
                            token_id=1,  # Placeholder
                            order_type=request.order_type,
                            transaction_type=exit_transaction,
                            product_type=position.get('product_type', 'MIS'),
                            quantity=exit_quantity,
                            price=request.price,
                            exchange=request.exchange,
                            status="PENDING",
                            remarks=f"Exit order for {token_mofsl_id}"
                        )
                        
                        db.add(db_order)
                        
                    except Exception as e:
                        client_errors.append(f"Position exit failed: {str(e)}")
                        logger.error(f"Failed to exit position for {client.client_code}: {e}")
                
                db.commit()
                
                return {
                    "client_id": client.id,
                    "client_code": client.client_code,
                    "success": len(client_errors) == 0,
                    "positions_exited": client_exit_count,
                    "total_positions": len(positions),
                    "error_message": "; ".join(client_errors) if client_errors else None
                }
                
            except Exception as e:
                logger.error(f"Client exit failed for {client.client_code}: {e}")
                return {
                    "client_id": client.id,
                    "client_code": client.client_code,
                    "success": False,
                    "error_message": str(e),
                    "positions_exited": 0,
                    "total_positions": len(positions)
                }
        
        # Execute exits concurrently with limited concurrency
        semaphore = asyncio.Semaphore(5)  # Limit concurrent exits
        
        async def execute_with_semaphore(client_positions):
            async with semaphore:
                return await execute_client_exit(client_positions)
        
        tasks = [execute_with_semaphore(cp) for cp in clients_to_exit]
        client_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        final_results = []
        for result in client_results:
            if isinstance(result, Exception):
                final_results.append({
                    "client_id": 0,
                    "client_code": "UNKNOWN",
                    "success": False,
                    "error_message": str(result),
                    "positions_exited": 0
                })
            else:
                final_results.append(result)
        
        # Add any clients that had no positions
        final_results.extend(exit_results)
        
        # Calculate summary
        successful_exits = [r for r in final_results if r["success"]]
        total_positions_exited = sum(r["positions_exited"] for r in final_results)
        
        total_time = int((datetime.now() - execution_start).total_seconds() * 1000)
        
        return {
            "success": len(successful_exits) > 0,
            "message": f"Exit operation completed for token {token_mofsl_id}",
            "summary": {
                "token_mofsl_id": token_mofsl_id,
                "clients_processed": len(clients),
                "clients_with_positions": len(clients_to_exit),
                "successful_exits": len(successful_exits),
                "total_positions_exited": total_positions_exited,
                "execution_time_ms": total_time,
                "dry_run": request.dry_run
            },
            "results": final_results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Exit operation failed for token {token_mofsl_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Exit operation failed: {str(e)}"
        )

# =============================================================================
# ORDER STATUS AND MANAGEMENT ENDPOINTS
# =============================================================================

@router.get("/status/{order_id}")
async def get_order_status(
    order_id: str,
    client_id: int,
    segment: str = "interactive",
    db: Session = Depends(get_db)
):
    """
    Get status of a specific order
    
    Args:
        order_id (str): Order ID to check
        client_id (int): Client ID
        segment (str): Credential segment
        db (Session): Database session
        
    Returns:
        dict: Order status information
    """
    logger.info(f"Getting status for order {order_id}")
    
    try:
        # Get client
        client = await get_client_with_validation(client_id, segment, db)
        
        # Get order status from MOFSL
        auth_token = await mofsl_wrapper.authenticate_client(client, segment)
        order_status = await mofsl_wrapper.get_order_status(
            auth_token.token, 
            order_id, 
            client.client_code
        )
        
        return {
            "success": True,
            "message": "Order status retrieved successfully",
            "data": {
                "order_id": order_id,
                "client_code": client.client_code,
                "status": order_status,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting order status for {order_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get order status: {str(e)}"
        )

@router.post("/cancel/{order_id}")
async def cancel_order(
    order_id: str,
    client_id: int,
    segment: str = "interactive",
    db: Session = Depends(get_db)
):
    """
    Cancel a specific order
    
    Args:
        order_id (str): Order ID to cancel
        client_id (int): Client ID
        segment (str): Credential segment
        db (Session): Database session
        
    Returns:
        dict: Cancellation result
    """
    logger.info(f"Canceling order {order_id} for client {client_id}")
    
    try:
        # Get client
        client = await get_client_with_validation(client_id, segment, db)
        
        # Cancel order through MOFSL
        auth_token = await mofsl_wrapper.authenticate_client(client, segment)
        success = await mofsl_wrapper.cancel_order(
            auth_token.token,
            order_id,
            client.client_code
        )
        
        if success:
            # Update database record if exists
            db_order = db.query(OrderModel).filter(
                OrderModel.order_id == order_id,
                OrderModel.client_id == client_id
            ).first()
            
            if db_order:
                db_order.status = "CANCELLED"
                db.commit()
        
        return {
            "success": success,
            "message": "Order cancelled successfully" if success else "Order cancellation failed",
            "data": {
                "order_id": order_id,
                "client_code": client.client_code,
                "cancelled": success,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error canceling order {order_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel order: {str(e)}"
        )

@router.get("/health")
async def orders_health_check():
    """
    Health check for orders service
    
    Returns:
        dict: Health status
    """
    return {
        "status": "healthy",
        "service": "Orders API",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }