# File: debug_imports.py
# Run this script to identify import issues

print("=== Testing Individual Imports ===")

try:
    print("1. Testing FastAPI import...")
    from fastapi import APIRouter, Depends, HTTPException, status, Query
    print("✅ FastAPI imports successful")
except Exception as e:
    print(f"❌ FastAPI import error: {e}")

try:
    print("2. Testing SQLAlchemy import...")
    from sqlalchemy.orm import Session
    print("✅ SQLAlchemy imports successful")
except Exception as e:
    print(f"❌ SQLAlchemy import error: {e}")

try:
    print("3. Testing typing imports...")
    from typing import List, Optional
    print("✅ Typing imports successful")
except Exception as e:
    print(f"❌ Typing import error: {e}")

try:
    print("4. Testing logging import...")
    import logging
    print("✅ Logging import successful")
except Exception as e:
    print(f"❌ Logging import error: {e}")

try:
    print("5. Testing database import...")
    from app.db.database import get_db
    print("✅ Database import successful")
except Exception as e:
    print(f"❌ Database import error: {e}")

try:
    print("6. Testing models import...")
    from app.models.models import Client as ClientModel
    print("✅ Models import successful")
except Exception as e:
    print(f"❌ Models import error: {e}")

try:
    print("7. Testing schemas import...")
    from app.schemas.schemas import (
        Client, ClientCreate, ClientUpdate, ClientResponse, ClientListResponse,
        ClientCredentials, ClientWithCredentials
    )
    print("✅ Schemas import successful")
except Exception as e:
    print(f"❌ Schemas import error: {e}")

try:
    print("8. Testing security import...")
    from app.core.security import encrypt_data, decrypt_data
    print("✅ Security import successful")
except Exception as e:
    print(f"❌ Security import error: {e}")

print("\n=== Import Test Complete ===")