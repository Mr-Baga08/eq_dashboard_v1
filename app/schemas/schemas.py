# File: /app/schemas/schemas.py
from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

# =============================================================================
# BASE SCHEMAS
# =============================================================================

class UserBase(BaseModel):
    """Base User schema with common attributes"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=100)
    is_active: bool = True
    is_superuser: bool = False

class ClientBase(BaseModel):
    """Base Client schema with common attributes"""
    client_code: str = Field(..., min_length=3, max_length=20)
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, pattern=r'^\d{10,15}$')
    is_active: bool = True
    risk_profile: str = Field(default="moderate", pattern=r'^(conservative|moderate|aggressive)$')
    max_daily_loss: Optional[Decimal] = Field(None, ge=0)
    max_position_size: Optional[Decimal] = Field(None, ge=0)

class TokenBase(BaseModel):
    """Base Token schema with common attributes"""
    token: str = Field(..., min_length=1, max_length=20)
    symbol: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    exchange: str = Field(..., pattern=r'^(NSE|BSE|MCX|NCDEX)$')
    segment: str = Field(..., pattern=r'^(EQ|FO|CD|CO)$')
    instrument_type: str = Field(..., pattern=r'^(EQ|FUT|OPT|CE|PE)$')
    strike_price: Optional[Decimal] = Field(None, ge=0)
    option_type: Optional[str] = Field(None, pattern=r'^(CE|PE)$')
    expiry_date: Optional[datetime] = None
    lot_size: int = Field(default=1, ge=1)
    tick_size: Decimal = Field(default=0.05, gt=0)
    is_active: bool = True

class OrderBase(BaseModel):
    """Base Order schema with common attributes"""
    client_id: int = Field(..., gt=0)
    token_id: int = Field(..., gt=0)
    order_type: str = Field(..., pattern=r'^(MKT|LMT|SLM|SL)$')
    transaction_type: str = Field(..., pattern=r'^(BUY|SELL)$')
    product_type: str = Field(..., pattern=r'^(MIS|CNC|NRML)$')
    quantity: int = Field(..., gt=0)
    price: Optional[Decimal] = Field(None, ge=0)
    trigger_price: Optional[Decimal] = Field(None, ge=0)
    disclosed_quantity: int = Field(default=0, ge=0)
    exchange: str = Field(..., pattern=r'^(NSE|BSE|MCX|NCDEX)$')
    validity: str = Field(default="DAY", pattern=r'^(DAY|IOC|GTD)$')
    remarks: Optional[str] = Field(None, max_length=500)

class PositionBase(BaseModel):
    """Base Position schema with common attributes"""
    client_id: int = Field(..., gt=0)
    token_id: int = Field(..., gt=0)
    product_type: str = Field(..., pattern=r'^(MIS|CNC|NRML)$')
    exchange: str = Field(..., pattern=r'^(NSE|BSE|MCX|NCDEX)$')

# =============================================================================
# CREATE SCHEMAS (for incoming data)
# =============================================================================

class UserCreate(UserBase):
    """Schema for creating a new user"""
    password: str = Field(..., min_length=8, max_length=100)
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class UserUpdate(BaseModel):
    """Schema for updating user data"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None

class ClientCreate(ClientBase):
    """Schema for creating a new client"""
    pass

class ClientUpdate(BaseModel):
    """Schema for updating client data"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, pattern=r'^\d{10,15}$')
    is_active: Optional[bool] = None
    risk_profile: Optional[str] = Field(None, pattern=r'^(conservative|moderate|aggressive)$')
    max_daily_loss: Optional[Decimal] = Field(None, ge=0)
    max_position_size: Optional[Decimal] = Field(None, ge=0)

class ClientCredentials(BaseModel):
    """Schema for updating client broker credentials"""
    broker_name: str = Field(..., pattern=r'^(mofsl_interactive|mofsl_commodity|zerodha)$')
    api_key: str = Field(..., min_length=1, max_length=500)
    secret_key: str = Field(..., min_length=1, max_length=500)
    user_id: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=100)

class TokenCreate(TokenBase):
    """Schema for creating a new token/instrument"""
    pass

class TokenUpdate(BaseModel):
    """Schema for updating token data"""
    symbol: Optional[str] = Field(None, min_length=1, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    is_active: Optional[bool] = None
    lot_size: Optional[int] = Field(None, ge=1)
    tick_size: Optional[Decimal] = Field(None, gt=0)

class OrderCreate(OrderBase):
    """Schema for creating a new order"""
    
    @validator('price')
    def validate_price_for_limit_orders(cls, v, values):
        """Validate price is provided for limit orders"""
        if values.get('order_type') in ['LMT', 'SL'] and v is None:
            raise ValueError('Price is required for limit and stop-loss orders')
        return v
    
    @validator('trigger_price')
    def validate_trigger_price_for_sl_orders(cls, v, values):
        """Validate trigger price is provided for stop-loss orders"""
        if values.get('order_type') in ['SLM', 'SL'] and v is None:
            raise ValueError('Trigger price is required for stop-loss orders')
        return v

class OrderUpdate(BaseModel):
    """Schema for updating order data"""
    order_type: Optional[str] = Field(None, pattern=r'^(MKT|LMT|SLM|SL)$')
    quantity: Optional[int] = Field(None, gt=0)
    price: Optional[Decimal] = Field(None, ge=0)
    trigger_price: Optional[Decimal] = Field(None, ge=0)
    disclosed_quantity: Optional[int] = Field(None, ge=0)
    validity: Optional[str] = Field(None, pattern=r'^(DAY|IOC|GTD)$')
    remarks: Optional[str] = Field(None, max_length=500)

# =============================================================================
# READ SCHEMAS (for outgoing data)
# =============================================================================

class User(UserBase):
    """Schema for user data returned by API"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    is_2fa_enabled: bool
    
    class Config:
        from_attributes = True  # Updated for Pydantic v2

class Client(ClientBase):
    """Schema for client data returned by API"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_active: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class ClientWithCredentials(Client):
    """Schema for client data with credentials (admin only)"""
    has_mofsl_interactive_credentials: bool = False
    has_mofsl_commodity_credentials: bool = False
    
    @validator('has_mofsl_interactive_credentials', pre=True, always=True)
    def check_mofsl_interactive_creds(cls, v, values):
        """Check if MOFSL Interactive credentials exist"""
        # This would be computed in the API endpoint
        return bool(v)
    
    @validator('has_mofsl_commodity_credentials', pre=True, always=True)
    def check_mofsl_commodity_creds(cls, v, values):
        """Check if MOFSL Commodity credentials exist"""
        # This would be computed in the API endpoint
        return bool(v)

class Token(TokenBase):
    """Schema for token data returned by API"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class Order(OrderBase):
    """Schema for order data returned by API"""
    id: int
    order_id: str
    broker_order_id: Optional[str] = None
    status: str
    filled_quantity: int
    average_price: Optional[Decimal] = None
    order_time: datetime
    update_time: Optional[datetime] = None
    exchange_time: Optional[datetime] = None
    
    # Related data
    client: Optional[Client] = None
    token: Optional[Token] = None
    
    class Config:
        from_attributes = True

class Trade(BaseModel):
    """Schema for trade data returned by API"""
    id: int
    trade_id: str
    client_id: int
    token_id: int
    order_id: int
    transaction_type: str
    quantity: int
    price: Decimal
    value: Decimal
    brokerage: Decimal
    exchange_charges: Decimal
    gst: Decimal
    stt: Decimal
    stamp_duty: Decimal
    total_charges: Decimal
    net_amount: Decimal
    trade_time: datetime
    exchange_time: Optional[datetime] = None
    exchange: str
    
    # Related data
    client: Optional[Client] = None
    token: Optional[Token] = None
    
    class Config:
        from_attributes = True

class Position(PositionBase):
    """Schema for position data returned by API"""
    id: int
    net_quantity: int
    average_price: Decimal
    day_buy_quantity: int
    day_buy_value: Decimal
    day_sell_quantity: int
    day_sell_value: Decimal
    overnight_quantity: int
    overnight_value: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    total_pnl: Decimal
    last_price: Optional[Decimal] = None
    market_value: Decimal
    position_date: datetime
    updated_at: Optional[datetime] = None
    
    # Related data
    client: Optional[Client] = None
    token: Optional[Token] = None
    
    class Config:
        from_attributes = True

class Margin(BaseModel):
    """Schema for margin data returned by API"""
    id: int
    client_id: int
    segment: str
    available_cash: Decimal
    available_margin: Decimal
    collateral_margin: Decimal
    used_margin: Decimal
    span_margin: Decimal
    exposure_margin: Decimal
    premium_present: Decimal
    total_margin_available: Decimal
    total_margin_used: Decimal
    net_margin: Decimal
    payin_amount: Decimal
    payout_amount: Decimal
    margin_date: datetime
    updated_at: Optional[datetime] = None
    
    # Related data
    client: Optional[Client] = None
    
    class Config:
        from_attributes = True

# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================

class ResponseBase(BaseModel):
    """Base response schema"""
    success: bool = True
    message: str = "Operation completed successfully"

class UserResponse(ResponseBase):
    """Response schema for user operations"""
    data: User

class UserListResponse(ResponseBase):
    """Response schema for user list operations"""
    data: List[User]
    total: int
    page: int
    per_page: int

class ClientResponse(ResponseBase):
    """Response schema for client operations"""
    data: Client

class ClientListResponse(ResponseBase):
    """Response schema for client list operations"""
    data: List[Client]
    total: int
    page: int
    per_page: int

class TokenResponse(ResponseBase):
    """Response schema for token operations"""
    data: Token

class TokenListResponse(ResponseBase):
    """Response schema for token list operations"""
    data: List[Token]
    total: int
    page: int
    per_page: int

class OrderResponse(ResponseBase):
    """Response schema for order operations"""
    data: Order

class OrderListResponse(ResponseBase):
    """Response schema for order list operations"""
    data: List[Order]
    total: int
    page: int
    per_page: int

class PositionResponse(ResponseBase):
    """Response schema for position operations"""
    data: Position

class PositionListResponse(ResponseBase):
    """Response schema for position list operations"""
    data: List[Position]
    total: int
    page: int
    per_page: int

class TradeListResponse(ResponseBase):
    """Response schema for trade list operations"""
    data: List[Trade]
    total: int
    page: int
    per_page: int

class MarginListResponse(ResponseBase):
    """Response schema for margin list operations"""
    data: List[Margin]

# =============================================================================
# AUTHENTICATION SCHEMAS
# =============================================================================

class UserLogin(BaseModel):
    """Schema for user login"""
    username: str
    password: str
    totp_code: Optional[str] = Field(None, pattern=r'^\d{6}$')

class Token(BaseModel):
    """Schema for JWT token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenData(BaseModel):
    """Schema for token data"""
    username: Optional[str] = None
    user_id: Optional[int] = None

# =============================================================================
# DASHBOARD SCHEMAS
# =============================================================================

class DashboardStats(BaseModel):
    """Schema for dashboard statistics"""
    total_clients: int
    active_clients: int
    total_orders_today: int
    total_trades_today: int
    total_pnl_today: Decimal
    total_margin_used: Decimal

class ClientPortfolioSummary(BaseModel):
    """Schema for client portfolio summary"""
    client_id: int
    client_name: str
    total_positions: int
    total_pnl: Decimal
    total_margin_used: Decimal
    last_activity: Optional[datetime] = None