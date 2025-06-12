# File: /app/models/models.py
from sqlalchemy import Column, Integer, String, DateTime, Numeric, Boolean, Text, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid

Base = declarative_base()

class User(Base):
    """Platform admin users table"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Two-factor authentication
    totp_secret = Column(String(32), nullable=True)
    is_2fa_enabled = Column(Boolean, default=False)

class Client(Base):
    """Managed trading clients table"""
    __tablename__ = "clients"
    
    id = Column(Integer, primary_key=True, index=True)
    client_code = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    phone = Column(String(15), nullable=True)
    
    # Status and configuration
    is_active = Column(Boolean, default=True)
    risk_profile = Column(String(20), default="moderate")  # conservative, moderate, aggressive
    max_daily_loss = Column(Numeric(15, 2), nullable=True)
    max_position_size = Column(Numeric(15, 2), nullable=True)
    
    # Encrypted broker credentials (MOFSL Interactive)
    encrypted_mofsl_api_key_interactive = Column(Text, nullable=True)
    encrypted_mofsl_secret_key_interactive = Column(Text, nullable=True)
    encrypted_mofsl_user_id_interactive = Column(Text, nullable=True)
    encrypted_mofsl_password_interactive = Column(Text, nullable=True)
    
    # Encrypted broker credentials (MOFSL Commodity)
    encrypted_mofsl_api_key_commodity = Column(Text, nullable=True)
    encrypted_mofsl_secret_key_commodity = Column(Text, nullable=True)
    encrypted_mofsl_user_id_commodity = Column(Text, nullable=True)
    encrypted_mofsl_password_commodity = Column(Text, nullable=True)
    
    # Additional broker credentials can be added here
    # encrypted_zerodha_api_key = Column(Text, nullable=True)
    # encrypted_zerodha_secret_key = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_active = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    orders = relationship("Order", back_populates="client", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="client", cascade="all, delete-orphan")
    positions = relationship("Position", back_populates="client", cascade="all, delete-orphan")
    margins = relationship("Margin", back_populates="client", cascade="all, delete-orphan")

class Token(Base):
    """Instrument master table"""
    __tablename__ = "tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(20), unique=True, index=True, nullable=False)  # Instrument token
    symbol = Column(String(50), index=True, nullable=False)
    name = Column(String(100), nullable=False)
    exchange = Column(String(10), index=True, nullable=False)  # NSE, BSE, MCX, etc.
    segment = Column(String(10), index=True, nullable=False)   # EQ, FO, CD, etc.
    instrument_type = Column(String(10), nullable=False)       # EQ, FUT, OPT, etc.
    
    # Option specific fields
    strike_price = Column(Numeric(10, 2), nullable=True)
    option_type = Column(String(2), nullable=True)  # CE, PE
    expiry_date = Column(DateTime, nullable=True)
    
    # Contract specifications
    lot_size = Column(Integer, default=1)
    tick_size = Column(Numeric(10, 4), default=0.05)
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    orders = relationship("Order", back_populates="token")
    trades = relationship("Trade", back_populates="token")
    positions = relationship("Position", back_populates="token")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_token_exchange_segment', 'exchange', 'segment'),
        Index('idx_token_symbol_exchange', 'symbol', 'exchange'),
    )

class Order(Base):
    """Orders table"""
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String(50), unique=True, index=True, nullable=False)
    broker_order_id = Column(String(50), index=True, nullable=True)
    
    # Foreign keys
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    token_id = Column(Integer, ForeignKey("tokens.id"), nullable=False)
    
    # Order details
    order_type = Column(String(10), nullable=False)    # MKT, LMT, SLM, SL
    transaction_type = Column(String(4), nullable=False)  # BUY, SELL
    product_type = Column(String(10), nullable=False)  # MIS, CNC, NRML
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(10, 2), nullable=True)
    trigger_price = Column(Numeric(10, 2), nullable=True)
    disclosed_quantity = Column(Integer, default=0)
    
    # Order status and execution
    status = Column(String(15), index=True, nullable=False)  # PENDING, OPEN, COMPLETE, CANCELLED, REJECTED
    filled_quantity = Column(Integer, default=0)
    average_price = Column(Numeric(10, 2), nullable=True)
    
    # Timestamps
    order_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), onupdate=func.now())
    exchange_time = Column(DateTime(timezone=True), nullable=True)
    
    # Additional fields
    exchange = Column(String(10), nullable=False)
    validity = Column(String(10), default="DAY")  # DAY, IOC, GTD
    remarks = Column(Text, nullable=True)
    
    # Relationships
    client = relationship("Client", back_populates="orders")
    token = relationship("Token", back_populates="orders")
    trades = relationship("Trade", back_populates="order")
    
    # Indexes
    __table_args__ = (
        Index('idx_order_client_status', 'client_id', 'status'),
        Index('idx_order_time', 'order_time'),
    )

class Trade(Base):
    """Trades/Executions table"""
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    trade_id = Column(String(50), unique=True, index=True, nullable=False)
    
    # Foreign keys
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    token_id = Column(Integer, ForeignKey("tokens.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    
    # Trade details
    transaction_type = Column(String(4), nullable=False)  # BUY, SELL
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    value = Column(Numeric(15, 2), nullable=False)
    
    # Charges and fees
    brokerage = Column(Numeric(10, 2), default=0)
    exchange_charges = Column(Numeric(10, 2), default=0)
    gst = Column(Numeric(10, 2), default=0)
    stt = Column(Numeric(10, 2), default=0)
    stamp_duty = Column(Numeric(10, 2), default=0)
    total_charges = Column(Numeric(10, 2), default=0)
    net_amount = Column(Numeric(15, 2), nullable=False)
    
    # Timestamps
    trade_time = Column(DateTime(timezone=True), server_default=func.now())
    exchange_time = Column(DateTime(timezone=True), nullable=True)
    
    # Additional fields
    exchange = Column(String(10), nullable=False)
    
    # Relationships
    client = relationship("Client", back_populates="trades")
    token = relationship("Token", back_populates="trades")
    order = relationship("Order", back_populates="trades")
    
    # Indexes
    __table_args__ = (
        Index('idx_trade_client_date', 'client_id', 'trade_time'),
        Index('idx_trade_token_date', 'token_id', 'trade_time'),
    )

class Position(Base):
    """Positions table"""
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    token_id = Column(Integer, ForeignKey("tokens.id"), nullable=False)
    
    # Position details
    product_type = Column(String(10), nullable=False)  # MIS, CNC, NRML
    net_quantity = Column(Integer, default=0)
    average_price = Column(Numeric(10, 2), default=0)
    
    # Day positions
    day_buy_quantity = Column(Integer, default=0)
    day_buy_value = Column(Numeric(15, 2), default=0)
    day_sell_quantity = Column(Integer, default=0)
    day_sell_value = Column(Numeric(15, 2), default=0)
    
    # Overnight positions
    overnight_quantity = Column(Integer, default=0)
    overnight_value = Column(Numeric(15, 2), default=0)
    
    # P&L calculations
    realized_pnl = Column(Numeric(15, 2), default=0)
    unrealized_pnl = Column(Numeric(15, 2), default=0)
    total_pnl = Column(Numeric(15, 2), default=0)
    
    # Current market data
    last_price = Column(Numeric(10, 2), nullable=True)
    market_value = Column(Numeric(15, 2), default=0)
    
    # Timestamps
    position_date = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Additional fields
    exchange = Column(String(10), nullable=False)
    
    # Relationships
    client = relationship("Client", back_populates="positions")
    token = relationship("Token", back_populates="positions")
    
    # Unique constraint to prevent duplicate positions
    __table_args__ = (
        Index('idx_position_client_token_product', 'client_id', 'token_id', 'product_type', unique=True),
        Index('idx_position_date', 'position_date'),
    )

class Margin(Base):
    """Margin/Funds table"""
    __tablename__ = "margins"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    
    # Margin details
    segment = Column(String(10), nullable=False)  # EQ, FO, CD
    
    # Available margins
    available_cash = Column(Numeric(15, 2), default=0)
    available_margin = Column(Numeric(15, 2), default=0)
    collateral_margin = Column(Numeric(15, 2), default=0)
    
    # Used margins
    used_margin = Column(Numeric(15, 2), default=0)
    span_margin = Column(Numeric(15, 2), default=0)
    exposure_margin = Column(Numeric(15, 2), default=0)
    premium_present = Column(Numeric(15, 2), default=0)
    
    # Total margins
    total_margin_available = Column(Numeric(15, 2), default=0)
    total_margin_used = Column(Numeric(15, 2), default=0)
    net_margin = Column(Numeric(15, 2), default=0)
    
    # Additional fields
    payin_amount = Column(Numeric(15, 2), default=0)
    payout_amount = Column(Numeric(15, 2), default=0)
    
    # Timestamps
    margin_date = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    client = relationship("Client", back_populates="margins")
    
    # Unique constraint
    __table_args__ = (
        Index('idx_margin_client_segment_date', 'client_id', 'segment', 'margin_date', unique=True),
    )