# File: /app/api/clients.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from app.db.database import get_db
from app.models.models import Client as ClientModel
from app.schemas.schemas import (
    Client, ClientCreate, ClientUpdate, ClientResponse, ClientListResponse,
    ClientCredentials, ClientWithCredentials
)
from app.core.security import encrypt_data, decrypt_data

logger = logging.getLogger(__name__)

# Create router for client endpoints
router = APIRouter(
    prefix="/admin/clients",
    tags=["Client Management"],
    responses={404: {"description": "Not found"}}
)

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def encrypt_client_credentials(credentials_data: dict) -> dict:
    """
    Encrypt client credentials for database storage
    
    Args:
        credentials_data (dict): Dictionary containing credential fields
        
    Returns:
        dict: Dictionary with encrypted credential fields
    """
    encrypted_fields = {}
    
    # Map of input fields to database field names
    field_mapping = {
        "mofsl_interactive": {
            "api_key": "encrypted_mofsl_api_key_interactive",
            "secret_key": "encrypted_mofsl_secret_key_interactive", 
            "user_id": "encrypted_mofsl_user_id_interactive",
            "password": "encrypted_mofsl_password_interactive"
        },
        "mofsl_commodity": {
            "api_key": "encrypted_mofsl_api_key_commodity",
            "secret_key": "encrypted_mofsl_secret_key_commodity",
            "user_id": "encrypted_mofsl_user_id_commodity", 
            "password": "encrypted_mofsl_password_commodity"
        }
    }
    
    # Encrypt credentials for each broker segment
    for segment, fields in field_mapping.items():
        if segment in credentials_data:
            segment_data = credentials_data[segment]
            for field_key, db_field in fields.items():
                if field_key in segment_data and segment_data[field_key]:
                    encrypted_fields[db_field] = encrypt_data(str(segment_data[field_key]))
                    logger.debug(f"Encrypted {segment}.{field_key}")
    
    return encrypted_fields

def check_credential_existence(client: ClientModel) -> dict:
    """
    Check which credentials exist for a client (without decrypting)
    
    Args:
        client (ClientModel): Client database model
        
    Returns:
        dict: Dictionary indicating which credentials exist
    """
    return {
        "has_mofsl_interactive_credentials": bool(
            client.encrypted_mofsl_api_key_interactive and
            client.encrypted_mofsl_secret_key_interactive and
            client.encrypted_mofsl_user_id_interactive and
            client.encrypted_mofsl_password_interactive
        ),
        "has_mofsl_commodity_credentials": bool(
            client.encrypted_mofsl_api_key_commodity and
            client.encrypted_mofsl_secret_key_commodity and
            client.encrypted_mofsl_user_id_commodity and
            client.encrypted_mofsl_password_commodity
        )
    }

def validate_client_code_unique(db: Session, client_code: str, exclude_id: Optional[int] = None) -> bool:
    """
    Validate that client code is unique
    
    Args:
        db (Session): Database session
        client_code (str): Client code to validate
        exclude_id (Optional[int]): Client ID to exclude from check (for updates)
        
    Returns:
        bool: True if unique, False if duplicate exists
    """
    query = db.query(ClientModel).filter(ClientModel.client_code == client_code)
    if exclude_id:
        query = query.filter(ClientModel.id != exclude_id)
    
    existing_client = query.first()
    return existing_client is None

# =============================================================================
# CLIENT CRUD ENDPOINTS
# =============================================================================

@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    client_data: ClientCreate,
    credentials: Optional[dict] = None,
    db: Session = Depends(get_db)
):
    """
    Create a new client
    
    Args:
        client_data (ClientCreate): Client creation data
        credentials (Optional[dict]): Optional broker credentials
        db (Session): Database session
        
    Returns:
        ClientResponse: Created client data
        
    Raises:
        HTTPException: If validation fails or client code already exists
    """
    logger.info(f"Creating new client: {client_data.client_code}")
    
    try:
        # Validate client code uniqueness
        if not validate_client_code_unique(db, client_data.client_code):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Client code '{client_data.client_code}' already exists"
            )
        
        # Validate email uniqueness
        existing_email = db.query(ClientModel).filter(ClientModel.email == client_data.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email '{client_data.email}' already exists"
            )
        
        # Create client model
        client_dict = client_data.model_dump()
        
        # Encrypt credentials if provided
        if credentials:
            encrypted_creds = encrypt_client_credentials(credentials)
            client_dict.update(encrypted_creds)
        
        # Create database record
        db_client = ClientModel(**client_dict)
        db.add(db_client)
        db.commit()
        db.refresh(db_client)
        
        logger.info(f"Client created successfully: {db_client.client_code} (ID: {db_client.id})")
        
        # Return response
        client_response = Client.model_validate(db_client)
        return ClientResponse(
            success=True,
            message="Client created successfully",
            data=client_response
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating client {client_data.client_code}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create client"
        )

@router.get("/", response_model=ClientListResponse)
async def list_clients(
    skip: int = Query(0, ge=0, description="Number of clients to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of clients to return"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    risk_profile: Optional[str] = Query(None, description="Filter by risk profile"),
    search: Optional[str] = Query(None, description="Search by client code or name"),
    db: Session = Depends(get_db)
):
    """
    List all clients with optional filtering and pagination
    
    Args:
        skip (int): Number of records to skip
        limit (int): Number of records to return
        is_active (Optional[bool]): Filter by active status
        risk_profile (Optional[str]): Filter by risk profile
        search (Optional[str]): Search term
        db (Session): Database session
        
    Returns:
        ClientListResponse: List of clients with pagination info
    """
    logger.info(f"Listing clients: skip={skip}, limit={limit}")
    
    try:
        # Build query
        query = db.query(ClientModel)
        
        # Apply filters
        if is_active is not None:
            query = query.filter(ClientModel.is_active == is_active)
        
        if risk_profile:
            query = query.filter(ClientModel.risk_profile == risk_profile)
        
        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                (ClientModel.client_code.ilike(search_filter)) |
                (ClientModel.name.ilike(search_filter)) |
                (ClientModel.email.ilike(search_filter))
            )
        
        # Get total count
        total = query.count()
        
        # Apply pagination and get results
        clients = query.offset(skip).limit(limit).all()
        
        # Convert to response format (excluding encrypted fields)
        client_list = []
        for client in clients:
            client_data = Client.model_validate(client)
            client_list.append(client_data)
        
        logger.info(f"Retrieved {len(client_list)} clients (total: {total})")
        
        return ClientListResponse(
            success=True,
            message=f"Retrieved {len(client_list)} clients",
            data=client_list,
            total=total,
            page=skip // limit + 1,
            per_page=limit
        )
        
    except Exception as e:
        logger.error(f"Error listing clients: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve clients"
        )

@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: int,
    include_credentials: bool = Query(False, description="Include credential status"),
    db: Session = Depends(get_db)
):
    """
    Get a specific client by ID
    
    Args:
        client_id (int): Client ID
        include_credentials (bool): Whether to include credential status
        db (Session): Database session
        
    Returns:
        ClientResponse: Client data
        
    Raises:
        HTTPException: If client not found
    """
    logger.info(f"Getting client: {client_id}")
    
    try:
        # Get client from database
        client = db.query(ClientModel).filter(ClientModel.id == client_id).first()
        
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Client with ID {client_id} not found"
            )
        
        # Convert to response format
        if include_credentials:
            # Include credential existence flags
            client_data = ClientWithCredentials.model_validate(client)
            cred_status = check_credential_existence(client)
            client_data.has_mofsl_interactive_credentials = cred_status["has_mofsl_interactive_credentials"]
            client_data.has_mofsl_commodity_credentials = cred_status["has_mofsl_commodity_credentials"]
        else:
            client_data = Client.model_validate(client)
        
        logger.info(f"Retrieved client: {client.client_code}")
        
        return ClientResponse(
            success=True,
            message="Client retrieved successfully",
            data=client_data
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error getting client {client_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve client"
        )

@router.put("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: int,
    client_update: ClientUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a client
    
    Args:
        client_id (int): Client ID
        client_update (ClientUpdate): Client update data
        db (Session): Database session
        
    Returns:
        ClientResponse: Updated client data
        
    Raises:
        HTTPException: If client not found or validation fails
    """
    logger.info(f"Updating client: {client_id}")
    
    try:
        # Get existing client
        client = db.query(ClientModel).filter(ClientModel.id == client_id).first()
        
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Client with ID {client_id} not found"
            )
        
        # Validate email uniqueness if email is being updated
        if client_update.email and client_update.email != client.email:
            existing_email = db.query(ClientModel).filter(
                ClientModel.email == client_update.email,
                ClientModel.id != client_id
            ).first()
            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Email '{client_update.email}' already exists"
                )
        
        # Update fields
        update_data = client_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(client, field, value)
        
        # Commit changes
        db.commit()
        db.refresh(client)
        
        logger.info(f"Client updated successfully: {client.client_code}")
        
        # Return updated client
        client_data = Client.model_validate(client)
        return ClientResponse(
            success=True,
            message="Client updated successfully",
            data=client_data
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating client {client_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update client"
        )

@router.delete("/{client_id}")
async def delete_client(
    client_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a client (soft delete - mark as inactive)
    
    Args:
        client_id (int): Client ID
        db (Session): Database session
        
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: If client not found
    """
    logger.info(f"Deleting client: {client_id}")
    
    try:
        # Get existing client
        client = db.query(ClientModel).filter(ClientModel.id == client_id).first()
        
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Client with ID {client_id} not found"
            )
        
        # Soft delete - mark as inactive
        client.is_active = False
        db.commit()
        
        logger.info(f"Client soft deleted: {client.client_code}")
        
        return {
            "success": True,
            "message": f"Client {client.client_code} deleted successfully"
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting client {client_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete client"
        )

# =============================================================================
# CREDENTIAL MANAGEMENT ENDPOINTS
# =============================================================================

@router.put("/{client_id}/credentials", response_model=ClientResponse)
async def update_client_credentials(
    client_id: int,
    credentials: ClientCredentials,
    db: Session = Depends(get_db)
):
    """
    Update client broker credentials
    
    Args:
        client_id (int): Client ID
        credentials (ClientCredentials): New credentials
        db (Session): Database session
        
    Returns:
        ClientResponse: Updated client data
        
    Raises:
        HTTPException: If client not found or credentials invalid
    """
    logger.info(f"Updating credentials for client: {client_id}")
    
    try:
        # Get existing client
        client = db.query(ClientModel).filter(ClientModel.id == client_id).first()
        
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Client with ID {client_id} not found"
            )
        
        # Encrypt and update credentials based on broker
        broker_name = credentials.broker_name
        
        if broker_name == "mofsl_interactive":
            client.encrypted_mofsl_api_key_interactive = encrypt_data(credentials.api_key)
            client.encrypted_mofsl_secret_key_interactive = encrypt_data(credentials.secret_key)
            client.encrypted_mofsl_user_id_interactive = encrypt_data(credentials.user_id)
            client.encrypted_mofsl_password_interactive = encrypt_data(credentials.password)
        elif broker_name == "mofsl_commodity":
            client.encrypted_mofsl_api_key_commodity = encrypt_data(credentials.api_key)
            client.encrypted_mofsl_secret_key_commodity = encrypt_data(credentials.secret_key)
            client.encrypted_mofsl_user_id_commodity = encrypt_data(credentials.user_id)
            client.encrypted_mofsl_password_commodity = encrypt_data(credentials.password)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported broker: {broker_name}"
            )
        
        # Commit changes
        db.commit()
        db.refresh(client)
        
        logger.info(f"Credentials updated for client {client.client_code} - {broker_name}")
        
        # Return updated client (without credentials)
        client_data = Client.model_validate(client)
        return ClientResponse(
            success=True,
            message=f"Credentials updated successfully for {broker_name}",
            data=client_data
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating credentials for client {client_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update credentials"
        )

@router.get("/{client_id}/credentials/status")
async def get_credential_status(
    client_id: int,
    db: Session = Depends(get_db)
):
    """
    Get credential status for a client (which brokers have credentials configured)
    
    Args:
        client_id (int): Client ID
        db (Session): Database session
        
    Returns:
        dict: Credential status information
        
    Raises:
        HTTPException: If client not found
    """
    logger.info(f"Getting credential status for client: {client_id}")
    
    try:
        # Get existing client
        client = db.query(ClientModel).filter(ClientModel.id == client_id).first()
        
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Client with ID {client_id} not found"
            )
        
        # Check credential existence
        cred_status = check_credential_existence(client)
        
        return {
            "success": True,
            "message": "Credential status retrieved successfully",
            "data": {
                "client_id": client_id,
                "client_code": client.client_code,
                "credentials": cred_status
            }
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error getting credential status for client {client_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get credential status"
        )