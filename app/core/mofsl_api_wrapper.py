# File: /app/core/mofsl_api_wrapper.py
import httpx
import pyotp
import asyncio
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from enum import Enum

from app.core.security import decrypt_data
from app.schemas.schemas import Client

# Configure logging
logger = logging.getLogger(__name__)

class MOFSLEnvironment(Enum):
    """MOFSL API Environment Enum"""
    UAT = "UAT"
    PRODUCTION = "PRODUCTION"

@dataclass
class AuthToken:
    """Data class to store authentication token information"""
    token: str
    client_id: int
    expires_at: datetime
    token_type: str = "Bearer"
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
    
    def is_expired(self) -> bool:
        """Check if the token is expired"""
        return datetime.now(timezone.utc) >= self.expires_at
    
    def time_until_expiry(self) -> timedelta:
        """Get time remaining until token expires"""
        return self.expires_at - datetime.now(timezone.utc)
    
    def __str__(self):
        return f"AuthToken(client_id={self.client_id}, expires_at={self.expires_at}, expired={self.is_expired()})"

@dataclass
class MOFSLCredentials:
    """Data class to store decrypted MOFSL credentials"""
    api_key: str
    secret_key: str
    user_id: str
    password: str
    dob: Optional[str] = None  # Date of Birth for 2FA
    totp_secret: Optional[str] = None  # TOTP secret for generating codes
    
    def validate(self) -> bool:
        """Validate that all required credentials are present"""
        required_fields = [self.api_key, self.secret_key, self.user_id, self.password]
        return all(field and field.strip() for field in required_fields)

class MOFSLApiWrapper:
    """
    MOFSL API Wrapper Service
    
    This class handles authentication and communication with the MOFSL API.
    It manages token lifecycle, credential decryption, and API requests.
    """
    
    # MOFSL API Endpoints
    ENDPOINTS = {
        MOFSLEnvironment.UAT: {
            "base_url": "https://openapi.motilaloswaluat.com",
            "auth": "/rest/login/v3/authdirectapi",
            "logout": "/rest/login/v2/logout",
            "profile": "/rest/report/v1/profile",
            "positions": "/rest/report/v1/getposition",
            "holdings": "/rest/report/v1/getdpholding",
            "instruments": "/rest/report/v1/getscripsbyexchangename",
            "place_order": "/rest/secure/v1/placeorder",
            "modify_order": "/rest/secure/v1/modifyorder",
            "cancel_order": "/rest/secure/v1/cancelorder",
            "order_status": "/rest/report/v1/getorderdetail",
            "order_book": "/rest/report/v1/getorderbook"
        },
        MOFSLEnvironment.PRODUCTION: {
            "base_url": "https://openapi.motilaloswal.com",
            "auth": "/rest/login/v3/authdirectapi", 
            "logout": "/rest/login/v2/logout",
            "profile": "/rest/report/v1/profile",
            "positions": "/rest/report/v1/getposition",
            "holdings": "/rest/report/v1/getdpholding",
            "instruments": "/rest/report/v1/getscripsbyexchangename",
            "place_order": "/rest/secure/v1/placeorder",
            "modify_order": "/rest/secure/v1/modifyorder",
            "cancel_order": "/rest/secure/v1/cancelorder",
            "order_status": "/rest/report/v1/getorderdetail",
            "order_book": "/rest/report/v1/getorderbook"
        }
    }
    
    def __init__(self, environment: MOFSLEnvironment = MOFSLEnvironment.UAT, timeout: int = 30):
        """
        Initialize the MOFSL API Wrapper
        
        Args:
            environment (MOFSLEnvironment): API environment (UAT or PRODUCTION)
            timeout (int): HTTP request timeout in seconds
        """
        self.environment = environment
        self.timeout = timeout
        self.base_url = self.ENDPOINTS[environment]["base_url"]
        
        # Token storage - In production, this should be Redis or database
        self._auth_tokens: Dict[int, AuthToken] = {}
        
        # HTTP client configuration
        self._client_config = {
            "timeout": httpx.Timeout(timeout),
            "headers": {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "TradingPlatform/1.0"
            }
        }
        
        logger.info(f"MOFSL API Wrapper initialized for {environment.value} environment")
    
    def _decrypt_client_credentials(self, client: Client, segment: str = "interactive") -> MOFSLCredentials:
        """
        Decrypt client credentials from the database
        
        Args:
            client (Client): Client schema object with encrypted credentials
            segment (str): Credential segment ("interactive" or "commodity")
            
        Returns:
            MOFSLCredentials: Decrypted credentials
            
        Raises:
            ValueError: If credentials are missing or invalid
        """
        try:
            if segment == "interactive":
                encrypted_api_key = client.encrypted_mofsl_api_key_interactive
                encrypted_secret_key = client.encrypted_mofsl_secret_key_interactive
                encrypted_user_id = client.encrypted_mofsl_user_id_interactive
                encrypted_password = client.encrypted_mofsl_password_interactive
            elif segment == "commodity":
                encrypted_api_key = client.encrypted_mofsl_api_key_commodity
                encrypted_secret_key = client.encrypted_mofsl_secret_key_commodity
                encrypted_user_id = client.encrypted_mofsl_user_id_commodity
                encrypted_password = client.encrypted_mofsl_password_commodity
            else:
                raise ValueError(f"Invalid segment: {segment}")
            
            # Check if all required encrypted fields are present
            if not all([encrypted_api_key, encrypted_secret_key, encrypted_user_id, encrypted_password]):
                raise ValueError(f"Missing {segment} credentials for client {client.client_code}")
            
            # Decrypt credentials
            credentials = MOFSLCredentials(
                api_key=decrypt_data(encrypted_api_key),
                secret_key=decrypt_data(encrypted_secret_key),
                user_id=decrypt_data(encrypted_user_id),
                password=decrypt_data(encrypted_password)
            )
            
            # Validate decrypted credentials
            if not credentials.validate():
                raise ValueError(f"Invalid decrypted credentials for client {client.client_code}")
            
            logger.debug(f"Successfully decrypted {segment} credentials for client {client.client_code}")
            return credentials
            
        except Exception as e:
            logger.error(f"Error decrypting credentials for client {client.client_code}: {e}")
            raise ValueError(f"Failed to decrypt credentials: {str(e)}")
    
    def _generate_totp_code(self, totp_secret: str) -> str:
        """
        Generate a 6-digit TOTP code using the provided secret
        
        Args:
            totp_secret (str): Base32 encoded TOTP secret
            
        Returns:
            str: 6-digit TOTP code
            
        Raises:
            ValueError: If TOTP secret is invalid
        """
        try:
            totp = pyotp.TOTP(totp_secret)
            code = totp.now()
            logger.debug(f"Generated TOTP code: {code}")
            return code
        except Exception as e:
            logger.error(f"Error generating TOTP code: {e}")
            raise ValueError(f"Failed to generate TOTP code: {str(e)}")
    
    def _prepare_auth_payload(self, credentials: MOFSLCredentials) -> Dict[str, Any]:
        """
        Prepare authentication payload for MOFSL API
        
        Args:
            credentials (MOFSLCredentials): Decrypted client credentials
            
        Returns:
            Dict[str, Any]: Authentication payload
        """
        payload = {
            "userid": credentials.user_id,
            "password": credentials.password,
            "apikey": credentials.api_key
        }
        
        # Add 2FA if DOB is available
        if credentials.dob:
            payload["2FA"] = credentials.dob
        
        # Add TOTP if secret is available
        if credentials.totp_secret:
            try:
                totp_code = self._generate_totp_code(credentials.totp_secret)
                payload["totp"] = totp_code
            except Exception as e:
                logger.warning(f"Failed to generate TOTP code: {e}")
        
        logger.debug(f"Prepared auth payload for user: {credentials.user_id}")
        return payload
    
    def _calculate_token_expiry(self) -> datetime:
        """
        Calculate token expiry time (daily expiry at market close)
        
        Returns:
            datetime: Token expiry time
        """
        # MOFSL tokens typically expire at end of trading day
        # For now, set expiry to 8 hours from now or next day at 6 AM IST
        now = datetime.now(timezone.utc)
        
        # Convert to IST (UTC+5:30)
        ist_offset = timedelta(hours=5, minutes=30)
        ist_now = now + ist_offset
        
        # If it's before 6 AM IST, expire at 6 AM today, otherwise expire at 6 AM next day
        if ist_now.hour < 6:
            expiry_ist = ist_now.replace(hour=6, minute=0, second=0, microsecond=0)
        else:
            expiry_ist = (ist_now + timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)
        
        # Convert back to UTC
        expiry_utc = expiry_ist - ist_offset
        
        logger.debug(f"Token expiry calculated: {expiry_utc} UTC")
        return expiry_utc
    
    async def authenticate_client(self, client: Client, segment: str = "interactive", force_refresh: bool = False) -> AuthToken:
        """
        Authenticate client with MOFSL API
        
        Args:
            client (Client): Client schema object
            segment (str): Credential segment ("interactive" or "commodity")
            force_refresh (bool): Force token refresh even if valid token exists
            
        Returns:
            AuthToken: Authentication token with expiry information
            
        Raises:
            ValueError: If authentication fails or credentials are invalid
            httpx.HTTPError: If API request fails
        """
        logger.info(f"Authenticating client {client.client_code} for {segment} segment")
        
        # Check if we have a valid token for this client
        if not force_refresh and client.id in self._auth_tokens:
            existing_token = self._auth_tokens[client.id]
            if not existing_token.is_expired():
                logger.info(f"Using existing valid token for client {client.client_code}")
                return existing_token
        
        try:
            # Decrypt client credentials
            credentials = self._decrypt_client_credentials(client, segment)
            
            # Prepare authentication payload
            auth_payload = self._prepare_auth_payload(credentials)
            
            # Make authentication request
            auth_url = self.base_url + self.ENDPOINTS[self.environment]["auth"]
            
            async with httpx.AsyncClient(**self._client_config) as http_client:
                logger.debug(f"Making auth request to: {auth_url}")
                
                response = await http_client.post(
                    auth_url,
                    json=auth_payload
                )
                
                # Handle response
                await self._handle_auth_response(response, client)
                
                # Parse successful response
                response_data = response.json()
                
                # Extract auth token from response
                auth_token_value = self._extract_auth_token(response_data)
                
                # Create AuthToken object
                token_expiry = self._calculate_token_expiry()
                auth_token = AuthToken(
                    token=auth_token_value,
                    client_id=client.id,
                    expires_at=token_expiry
                )
                
                # Store token for future use
                self._auth_tokens[client.id] = auth_token
                
                logger.info(f"Successfully authenticated client {client.client_code}. Token expires at: {token_expiry}")
                return auth_token
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during authentication for client {client.client_code}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during authentication for client {client.client_code}: {e}")
            raise ValueError(f"Authentication failed: {str(e)}")
    
    async def _handle_auth_response(self, response: httpx.Response, client: Client) -> None:
        """
        Handle authentication response from MOFSL API
        
        Args:
            response (httpx.Response): HTTP response from auth API
            client (Client): Client object for logging
            
        Raises:
            ValueError: If authentication fails
        """
        if response.status_code == 200:
            try:
                response_data = response.json()
                
                # Check if response indicates success
                if response_data.get("status") == "success" or response_data.get("AuthToken"):
                    logger.info(f"Authentication successful for client {client.client_code}")
                    return
                else:
                    error_msg = response_data.get("message", "Unknown error")
                    logger.error(f"Authentication failed for client {client.client_code}: {error_msg}")
                    raise ValueError(f"Authentication failed: {error_msg}")
                    
            except ValueError:
                # Re-raise ValueError
                raise
            except Exception as e:
                logger.error(f"Error parsing auth response for client {client.client_code}: {e}")
                raise ValueError(f"Invalid response format: {str(e)}")
        else:
            logger.error(f"Authentication HTTP error for client {client.client_code}: {response.status_code}")
            try:
                error_data = response.json()
                error_msg = error_data.get("message", f"HTTP {response.status_code}")
            except:
                error_msg = f"HTTP {response.status_code}"
            
            raise ValueError(f"Authentication failed: {error_msg}")
    
    def _extract_auth_token(self, response_data: Dict[str, Any]) -> str:
        """
        Extract auth token from MOFSL API response
        
        Args:
            response_data (Dict[str, Any]): API response data
            
        Returns:
            str: Extracted auth token
            
        Raises:
            ValueError: If token cannot be extracted
        """
        # Try different possible token field names
        token_fields = ["AuthToken", "authToken", "token", "access_token"]
        
        for field in token_fields:
            if field in response_data and response_data[field]:
                logger.debug(f"Auth token extracted from field: {field}")
                return response_data[field]
        
        logger.error(f"No auth token found in response: {list(response_data.keys())}")
        raise ValueError("Auth token not found in response")
    
    def get_cached_token(self, client_id: int) -> Optional[AuthToken]:
        """
        Get cached authentication token for a client
        
        Args:
            client_id (int): Client ID
            
        Returns:
            Optional[AuthToken]: Cached token if valid, None otherwise
        """
        if client_id in self._auth_tokens:
            token = self._auth_tokens[client_id]
            if not token.is_expired():
                return token
            else:
                # Remove expired token
                del self._auth_tokens[client_id]
                logger.debug(f"Removed expired token for client {client_id}")
        
        return None
    
    def invalidate_token(self, client_id: int) -> bool:
        """
        Invalidate cached token for a client
        
        Args:
            client_id (int): Client ID
            
        Returns:
            bool: True if token was invalidated, False if no token existed
        """
        if client_id in self._auth_tokens:
            del self._auth_tokens[client_id]
            logger.info(f"Invalidated token for client {client_id}")
            return True
        return False
    
    def get_token_status(self, client_id: int) -> Dict[str, Any]:
        """
        Get token status information for a client
        
        Args:
            client_id (int): Client ID
            
        Returns:
            Dict[str, Any]: Token status information
        """
        if client_id not in self._auth_tokens:
            return {"exists": False, "expired": True}
        
        token = self._auth_tokens[client_id]
        return {
            "exists": True,
            "expired": token.is_expired(),
            "expires_at": token.expires_at.isoformat(),
            "time_until_expiry": str(token.time_until_expiry()),
            "created_at": token.created_at.isoformat()
        }
    
    async def logout_client(self, client: Client) -> bool:
        """
        Logout client from MOFSL API (placeholder for future implementation)
        
        Args:
            client (Client): Client schema object
            
        Returns:
            bool: True if logout successful
        """
        logger.info(f"Logout requested for client {client.client_code}")
        
        # Get cached token
        token = self.get_cached_token(client.id)
        if not token:
            logger.warning(f"No valid token found for client {client.client_code}")
            return True
        
        try:
            # Make logout request (placeholder implementation)
            logout_url = self.base_url + self.ENDPOINTS[self.environment]["logout"]
            
            async with httpx.AsyncClient(**self._client_config) as http_client:
                headers = {"Authorization": f"Bearer {token.token}"}
                response = await http_client.post(logout_url, headers=headers)
                
                if response.status_code == 200:
                    logger.info(f"Successfully logged out client {client.client_code}")
                else:
                    logger.warning(f"Logout response code {response.status_code} for client {client.client_code}")
            
            # Invalidate cached token regardless of logout response
            self.invalidate_token(client.id)
            return True
            
        except Exception as e:
            logger.error(f"Error during logout for client {client.client_code}: {e}")
            # Still invalidate the token
            self.invalidate_token(client.id)
            return False
    
    # =============================================================================
    # DATA FETCHING METHODS
    # =============================================================================
    
    async def _make_authenticated_request(self, endpoint: str, auth_token: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make an authenticated request to MOFSL API
        
        Args:
            endpoint (str): API endpoint path
            auth_token (str): Authentication token
            payload (Dict[str, Any]): Request payload
            
        Returns:
            Dict[str, Any]: API response data
            
        Raises:
            ValueError: If request fails or response is invalid
            httpx.HTTPError: If HTTP request fails
        """
        url = self.base_url + endpoint
        
        # Prepare headers with authentication
        headers = {
            **self._client_config["headers"],
            "Authorization": f"Bearer {auth_token}"
        }
        
        try:
            async with httpx.AsyncClient(timeout=self._client_config["timeout"]) as http_client:
                logger.debug(f"Making authenticated request to: {url}")
                
                response = await http_client.post(
                    url,
                    json=payload,
                    headers=headers
                )
                
                # Handle response
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        
                        # Check if response indicates success
                        if response_data.get("status") == "success" or "data" in response_data:
                            logger.debug(f"Authenticated request successful: {url}")
                            return response_data
                        else:
                            error_msg = response_data.get("message", "Unknown error")
                            logger.error(f"API error response: {error_msg}")
                            raise ValueError(f"API error: {error_msg}")
                            
                    except ValueError:
                        # Re-raise ValueError
                        raise
                    except Exception as e:
                        logger.error(f"Error parsing response from {url}: {e}")
                        raise ValueError(f"Invalid response format: {str(e)}")
                        
                else:
                    logger.error(f"HTTP error {response.status_code} from {url}")
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("message", f"HTTP {response.status_code}")
                    except:
                        error_msg = f"HTTP {response.status_code}"
                    
                    raise ValueError(f"Request failed: {error_msg}")
                    
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during request to {url}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during request to {url}: {e}")
            raise ValueError(f"Request failed: {str(e)}")
    
    async def get_positions(self, auth_token: str, client_code: str) -> List[Dict[str, Any]]:
        """
        Fetch client positions from MOFSL API
        
        Args:
            auth_token (str): Valid authentication token
            client_code (str): Client code for the positions
            
        Returns:
            List[Dict[str, Any]]: List of position data
            
        Raises:
            ValueError: If request fails or token is invalid
            httpx.HTTPError: If HTTP request fails
        """
        logger.info(f"Fetching positions for client: {client_code}")
        
        try:
            # Prepare request payload
            payload = {
                "clientcode": client_code
            }
            
            # Make authenticated request
            endpoint = self.ENDPOINTS[self.environment]["positions"]
            response_data = await self._make_authenticated_request(endpoint, auth_token, payload)
            
            # Extract positions data
            positions_data = response_data.get("data", [])
            
            # Ensure we return a list
            if not isinstance(positions_data, list):
                positions_data = [positions_data] if positions_data else []
            
            logger.info(f"Successfully fetched {len(positions_data)} positions for client {client_code}")
            return positions_data
            
        except Exception as e:
            logger.error(f"Error fetching positions for client {client_code}: {e}")
            raise
    
    async def get_holdings(self, auth_token: str, client_code: str) -> List[Dict[str, Any]]:
        """
        Fetch client holdings from MOFSL API
        
        Args:
            auth_token (str): Valid authentication token
            client_code (str): Client code for the holdings
            
        Returns:
            List[Dict[str, Any]]: List of holding data
            
        Raises:
            ValueError: If request fails or token is invalid
            httpx.HTTPError: If HTTP request fails
        """
        logger.info(f"Fetching holdings for client: {client_code}")
        
        try:
            # Prepare request payload
            payload = {
                "clientcode": client_code
            }
            
            # Make authenticated request
            endpoint = self.ENDPOINTS[self.environment]["holdings"]
            response_data = await self._make_authenticated_request(endpoint, auth_token, payload)
            
            # Extract holdings data
            holdings_data = response_data.get("data", [])
            
            # Ensure we return a list
            if not isinstance(holdings_data, list):
                holdings_data = [holdings_data] if holdings_data else []
            
            logger.info(f"Successfully fetched {len(holdings_data)} holdings for client {client_code}")
            return holdings_data
            
        except Exception as e:
            logger.error(f"Error fetching holdings for client {client_code}: {e}")
            raise
    
    async def search_instruments(self, auth_token: str, exchange: str) -> List[Dict[str, Any]]:
        """
        Search instruments by exchange from MOFSL API
        
        Args:
            auth_token (str): Valid authentication token
            exchange (str): Exchange name (e.g., "NSE", "BSE", "MCX")
            
        Returns:
            List[Dict[str, Any]]: List of instrument data
            
        Raises:
            ValueError: If request fails or exchange is invalid
            httpx.HTTPError: If HTTP request fails
        """
        logger.info(f"Searching instruments for exchange: {exchange}")
        
        # Validate exchange parameter
        valid_exchanges = ["NSE", "BSE", "MCX", "NCDEX", "CDS"]
        if exchange.upper() not in valid_exchanges:
            raise ValueError(f"Invalid exchange: {exchange}. Valid exchanges: {valid_exchanges}")
        
        try:
            # Prepare request payload
            payload = {
                "exchangename": exchange.upper()
            }
            
            # Make authenticated request
            endpoint = self.ENDPOINTS[self.environment]["instruments"]
            response_data = await self._make_authenticated_request(endpoint, auth_token, payload)
            
            # Extract instruments data
            instruments_data = response_data.get("data", [])
            
            # Ensure we return a list
            if not isinstance(instruments_data, list):
                instruments_data = [instruments_data] if instruments_data else []
            
            logger.info(f"Successfully fetched {len(instruments_data)} instruments for exchange {exchange}")
            return instruments_data
            
        except Exception as e:
            logger.error(f"Error searching instruments for exchange {exchange}: {e}")
            raise
    
    async def get_client_profile(self, auth_token: str, client_code: str) -> Dict[str, Any]:
        """
        Fetch client profile information from MOFSL API
        
        Args:
            auth_token (str): Valid authentication token
            client_code (str): Client code for the profile
            
        Returns:
            Dict[str, Any]: Client profile data
            
        Raises:
            ValueError: If request fails or token is invalid
            httpx.HTTPError: If HTTP request fails
        """
        logger.info(f"Fetching profile for client: {client_code}")
        
        try:
            # Prepare request payload
            payload = {
                "clientcode": client_code
            }
            
            # Make authenticated request
            endpoint = self.ENDPOINTS[self.environment]["profile"]
            response_data = await self._make_authenticated_request(endpoint, auth_token, payload)
            
            # Extract profile data
            profile_data = response_data.get("data", {})
            
            # Ensure we return a dict
            if not isinstance(profile_data, dict):
                profile_data = {}
            
            logger.info(f"Successfully fetched profile for client {client_code}")
            return profile_data
            
        except Exception as e:
            logger.error(f"Error fetching profile for client {client_code}: {e}")
            raise
    
    async def get_portfolio_summary(self, client: Client, segment: str = "interactive") -> Dict[str, Any]:
        """
        Get comprehensive portfolio summary for a client
        
        Args:
            client (Client): Client schema object
            segment (str): Credential segment ("interactive" or "commodity")
            
        Returns:
            Dict[str, Any]: Portfolio summary including positions, holdings, and profile
            
        Raises:
            ValueError: If authentication or data fetching fails
        """
        logger.info(f"Fetching portfolio summary for client {client.client_code}")
        
        try:
            # Authenticate client to get token
            auth_token = await self.authenticate_client(client, segment)
            
            # Fetch all portfolio data concurrently
            tasks = [
                self.get_positions(auth_token.token, client.client_code),
                self.get_holdings(auth_token.token, client.client_code),
                self.get_client_profile(auth_token.token, client.client_code)
            ]
            
            positions, holdings, profile = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle any exceptions from concurrent requests
            portfolio_summary = {
                "client_code": client.client_code,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "positions": positions if not isinstance(positions, Exception) else [],
                "holdings": holdings if not isinstance(holdings, Exception) else [],
                "profile": profile if not isinstance(profile, Exception) else {},
                "errors": []
            }
            
            # Log any errors that occurred
            if isinstance(positions, Exception):
                error_msg = f"Failed to fetch positions: {str(positions)}"
                portfolio_summary["errors"].append(error_msg)
                logger.error(error_msg)
            
            if isinstance(holdings, Exception):
                error_msg = f"Failed to fetch holdings: {str(holdings)}"
                portfolio_summary["errors"].append(error_msg)
                logger.error(error_msg)
            
            if isinstance(profile, Exception):
                error_msg = f"Failed to fetch profile: {str(profile)}"
                portfolio_summary["errors"].append(error_msg)
                logger.error(error_msg)
            
            logger.info(f"Portfolio summary completed for client {client.client_code}")
            return portfolio_summary
            
        except Exception as e:
            logger.error(f"Error fetching portfolio summary for client {client.client_code}: {e}")
            raise
    
    # =============================================================================
    # ORDER MANAGEMENT METHODS
    # =============================================================================
    
    def _map_order_to_mofsl_payload(self, order_details, client_code: str) -> Dict[str, Any]:
        """
        Map OrderCreate schema to MOFSL API payload format
        
        Args:
            order_details: OrderCreate schema object
            client_code (str): Client code for the order
            
        Returns:
            Dict[str, Any]: MOFSL API compatible payload
        """
        # Map order types
        order_type_mapping = {
            "MKT": "MARKET",
            "LMT": "LIMIT", 
            "SLM": "SL-M",
            "SL": "SL"
        }
        
        # Map transaction types
        transaction_type_mapping = {
            "BUY": "B",
            "SELL": "S"
        }
        
        # Map product types
        product_type_mapping = {
            "MIS": "MIS",  # Margin Intraday Square-off
            "CNC": "CNC",  # Cash and Carry
            "NRML": "NRML"  # Normal
        }
        
        # Map validity types
        validity_mapping = {
            "DAY": "DAY",
            "IOC": "IOC",
            "GTD": "GTD"
        }
        
        # Build the payload
        payload = {
            "clientcode": client_code,
            "symboltoken": str(order_details.token_id),  # Assuming token_id maps to symbol token
            "transactiontype": transaction_type_mapping.get(order_details.transaction_type, order_details.transaction_type),
            "ordertype": order_type_mapping.get(order_details.order_type, order_details.order_type),
            "producttype": product_type_mapping.get(order_details.product_type, order_details.product_type),
            "quantity": str(order_details.quantity),
            "exchange": order_details.exchange,
            "validity": validity_mapping.get(order_details.validity, "DAY")
        }
        
        # Add price for limit orders
        if order_details.price is not None:
            payload["price"] = str(float(order_details.price))
        
        # Add trigger price for stop-loss orders
        if order_details.trigger_price is not None:
            payload["triggerprice"] = str(float(order_details.trigger_price))
        
        # Add disclosed quantity if specified
        if order_details.disclosed_quantity and order_details.disclosed_quantity > 0:
            payload["disclosedquantity"] = str(order_details.disclosed_quantity)
        
        # Add remarks if provided
        if order_details.remarks:
            payload["remarks"] = order_details.remarks[:100]  # Limit remarks length
        
        logger.debug(f"Mapped order payload: {payload}")
        return payload
    
    async def place_order(self, auth_token: str, order_details, client_code: str) -> str:
        """
        Place a new order through MOFSL API
        
        Args:
            auth_token (str): Valid authentication token
            order_details: OrderCreate schema object with order details
            client_code (str): Client code for the order
            
        Returns:
            str: Unique order ID from MOFSL API
            
        Raises:
            ValueError: If order placement fails or validation errors occur
            httpx.HTTPError: If HTTP request fails
        """
        logger.info(f"Placing order for client {client_code}: {order_details.transaction_type} {order_details.quantity} @ {order_details.order_type}")
        
        try:
            # Validate order details
            self._validate_order_details(order_details)
            
            # Map order to MOFSL payload format
            payload = self._map_order_to_mofsl_payload(order_details, client_code)
            
            # Make authenticated request to place order
            endpoint = self.ENDPOINTS[self.environment]["place_order"]
            response_data = await self._make_authenticated_request(endpoint, auth_token, payload)
            
            # Extract unique order ID from response
            unique_order_id = self._extract_order_id(response_data)
            
            logger.info(f"Order placed successfully for client {client_code}. Order ID: {unique_order_id}")
            return unique_order_id
            
        except Exception as e:
            logger.error(f"Error placing order for client {client_code}: {e}")
            raise
    
    async def modify_order(self, auth_token: str, unique_order_id: str, order_modifications: Dict[str, Any], client_code: str) -> bool:
        """
        Modify an existing order through MOFSL API
        
        Args:
            auth_token (str): Valid authentication token
            unique_order_id (str): Unique order ID to modify
            order_modifications (Dict[str, Any]): Fields to modify (quantity, price, etc.)
            client_code (str): Client code for the order
            
        Returns:
            bool: True if modification successful
            
        Raises:
            ValueError: If order modification fails
            httpx.HTTPError: If HTTP request fails
        """
        logger.info(f"Modifying order {unique_order_id} for client {client_code}")
        
        try:
            # Prepare modification payload
            payload = {
                "clientcode": client_code,
                "uniqueorderid": unique_order_id
            }
            
            # Add modification fields
            if "quantity" in order_modifications:
                payload["quantity"] = str(order_modifications["quantity"])
            
            if "price" in order_modifications:
                payload["price"] = str(float(order_modifications["price"]))
            
            if "trigger_price" in order_modifications:
                payload["triggerprice"] = str(float(order_modifications["trigger_price"]))
            
            if "order_type" in order_modifications:
                order_type_mapping = {"MKT": "MARKET", "LMT": "LIMIT", "SLM": "SL-M", "SL": "SL"}
                payload["ordertype"] = order_type_mapping.get(order_modifications["order_type"], order_modifications["order_type"])
            
            if "validity" in order_modifications:
                payload["validity"] = order_modifications["validity"]
            
            if "disclosed_quantity" in order_modifications:
                payload["disclosedquantity"] = str(order_modifications["disclosed_quantity"])
            
            # Make authenticated request to modify order
            endpoint = self.ENDPOINTS[self.environment]["modify_order"]
            response_data = await self._make_authenticated_request(endpoint, auth_token, payload)
            
            # Check if modification was successful
            is_successful = self._check_order_operation_success(response_data, "modify")
            
            if is_successful:
                logger.info(f"Order {unique_order_id} modified successfully for client {client_code}")
            else:
                logger.error(f"Order modification failed for {unique_order_id}")
            
            return is_successful
            
        except Exception as e:
            logger.error(f"Error modifying order {unique_order_id} for client {client_code}: {e}")
            raise
    
    async def cancel_order(self, auth_token: str, unique_order_id: str, client_code: str) -> bool:
        """
        Cancel an existing order through MOFSL API
        
        Args:
            auth_token (str): Valid authentication token
            unique_order_id (str): Unique order ID to cancel
            client_code (str): Client code for the order
            
        Returns:
            bool: True if cancellation successful
            
        Raises:
            ValueError: If order cancellation fails
            httpx.HTTPError: If HTTP request fails
        """
        logger.info(f"Canceling order {unique_order_id} for client {client_code}")
        
        try:
            # Prepare cancellation payload
            payload = {
                "clientcode": client_code,
                "uniqueorderid": unique_order_id
            }
            
            # Make authenticated request to cancel order
            endpoint = self.ENDPOINTS[self.environment]["cancel_order"]
            response_data = await self._make_authenticated_request(endpoint, auth_token, payload)
            
            # Check if cancellation was successful
            is_successful = self._check_order_operation_success(response_data, "cancel")
            
            if is_successful:
                logger.info(f"Order {unique_order_id} canceled successfully for client {client_code}")
            else:
                logger.error(f"Order cancellation failed for {unique_order_id}")
            
            return is_successful
            
        except Exception as e:
            logger.error(f"Error canceling order {unique_order_id} for client {client_code}: {e}")
            raise
    
    async def get_order_status(self, auth_token: str, unique_order_id: str, client_code: str) -> Dict[str, Any]:
        """
        Get status of a specific order through MOFSL API
        
        Args:
            auth_token (str): Valid authentication token
            unique_order_id (str): Unique order ID to check
            client_code (str): Client code for the order
            
        Returns:
            Dict[str, Any]: Order status details
            
        Raises:
            ValueError: If order status fetch fails
            httpx.HTTPError: If HTTP request fails
        """
        logger.info(f"Fetching status for order {unique_order_id} for client {client_code}")
        
        try:
            # Prepare status request payload
            payload = {
                "clientcode": client_code,
                "uniqueorderid": unique_order_id
            }
            
            # Make authenticated request to get order status
            endpoint = self.ENDPOINTS[self.environment]["order_status"]
            response_data = await self._make_authenticated_request(endpoint, auth_token, payload)
            
            # Extract order status data
            order_status = response_data.get("data", {})
            
            logger.info(f"Order status fetched for {unique_order_id}")
            return order_status
            
        except Exception as e:
            logger.error(f"Error fetching order status for {unique_order_id}: {e}")
            raise
    
    async def get_order_book(self, auth_token: str, client_code: str) -> List[Dict[str, Any]]:
        """
        Get complete order book for a client through MOFSL API
        
        Args:
            auth_token (str): Valid authentication token
            client_code (str): Client code for the order book
            
        Returns:
            List[Dict[str, Any]]: List of all orders for the client
            
        Raises:
            ValueError: If order book fetch fails
            httpx.HTTPError: If HTTP request fails
        """
        logger.info(f"Fetching order book for client {client_code}")
        
        try:
            # Prepare order book request payload
            payload = {
                "clientcode": client_code
            }
            
            # Make authenticated request to get order book
            endpoint = self.ENDPOINTS[self.environment]["order_book"]
            response_data = await self._make_authenticated_request(endpoint, auth_token, payload)
            
            # Extract order book data
            order_book = response_data.get("data", [])
            
            # Ensure we return a list
            if not isinstance(order_book, list):
                order_book = [order_book] if order_book else []
            
            logger.info(f"Order book fetched for client {client_code}: {len(order_book)} orders")
            return order_book
            
        except Exception as e:
            logger.error(f"Error fetching order book for client {client_code}: {e}")
            raise
    
    def _validate_order_details(self, order_details) -> None:
        """
        Validate order details before placing order
        
        Args:
            order_details: OrderCreate schema object
            
        Raises:
            ValueError: If validation fails
        """
        # Check required fields
        if not order_details.quantity or order_details.quantity <= 0:
            raise ValueError("Order quantity must be greater than 0")
        
        # Validate price for limit orders
        if order_details.order_type in ["LMT", "SL"] and (not order_details.price or order_details.price <= 0):
            raise ValueError("Price is required and must be greater than 0 for limit orders")
        
        # Validate trigger price for stop-loss orders
        if order_details.order_type in ["SLM", "SL"] and (not order_details.trigger_price or order_details.trigger_price <= 0):
            raise ValueError("Trigger price is required and must be greater than 0 for stop-loss orders")
        
        # Validate disclosed quantity
        if order_details.disclosed_quantity and order_details.disclosed_quantity > order_details.quantity:
            raise ValueError("Disclosed quantity cannot be greater than total quantity")
        
        logger.debug("Order details validation passed")
    
    def _extract_order_id(self, response_data: Dict[str, Any]) -> str:
        """
        Extract unique order ID from MOFSL API response
        
        Args:
            response_data (Dict[str, Any]): API response data
            
        Returns:
            str: Extracted unique order ID
            
        Raises:
            ValueError: If order ID cannot be extracted
        """
        # Try different possible order ID field names
        order_id_fields = ["uniqueorderid", "orderid", "order_id", "orderId"]
        
        # Check in data section first
        data_section = response_data.get("data", {})
        if isinstance(data_section, dict):
            for field in order_id_fields:
                if field in data_section and data_section[field]:
                    logger.debug(f"Order ID extracted from data.{field}")
                    return str(data_section[field])
        
        # Check in root response
        for field in order_id_fields:
            if field in response_data and response_data[field]:
                logger.debug(f"Order ID extracted from {field}")
                return str(response_data[field])
        
        logger.error(f"No order ID found in response: {list(response_data.keys())}")
        raise ValueError("Order ID not found in response")
    
    def _check_order_operation_success(self, response_data: Dict[str, Any], operation: str) -> bool:
        """
        Check if order operation (modify/cancel) was successful
        
        Args:
            response_data (Dict[str, Any]): API response data
            operation (str): Operation type ("modify" or "cancel")
            
        Returns:
            bool: True if operation was successful
        """
        # Check for success indicators
        if response_data.get("status") == "success":
            return True
        
        # Check for success message
        message = response_data.get("message", "").lower()
        success_keywords = ["success", "successful", "completed", "done"]
        
        if any(keyword in message for keyword in success_keywords):
            return True
        
        # Check data section for success indicators
        data_section = response_data.get("data", {})
        if isinstance(data_section, dict):
            if data_section.get("status") == "success":
                return True
        
        logger.warning(f"Order {operation} operation may have failed: {response_data}")
        return False
    
    def __str__(self):
        return f"MOFSLApiWrapper(environment={self.environment.value}, cached_tokens={len(self._auth_tokens)})"


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def create_mofsl_wrapper(environment: str = "UAT") -> MOFSLApiWrapper:
    """
    Factory function to create MOFSL API Wrapper instance
    
    Args:
        environment (str): Environment name ("UAT" or "PRODUCTION")
        
    Returns:
        MOFSLApiWrapper: Configured wrapper instance
    """
    env = MOFSLEnvironment.UAT if environment.upper() == "UAT" else MOFSLEnvironment.PRODUCTION
    return MOFSLApiWrapper(environment=env)

# Global wrapper instance (can be used across the application)
mofsl_wrapper = create_mofsl_wrapper()

# =============================================================================
# TESTING UTILITIES (for development)
# =============================================================================

async def test_authentication():
    """
    Test authentication functionality (for development only)
    """
    print("=== Testing MOFSL Authentication ===")
    
    # This would require a real client object with encrypted credentials
    # For now, just test the wrapper initialization
    wrapper = create_mofsl_wrapper("UAT")
    print(f"✅ MOFSL Wrapper created: {wrapper}")
    
    # Test token status for non-existent client
    status = wrapper.get_token_status(999)
    print(f"Token status for non-existent client: {status}")
    
    print("Authentication test completed (requires real client data for full test)")

async def test_data_fetching():
    """
    Test data fetching functionality (for development only)
    """
    print("=== Testing MOFSL Data Fetching ===")
    
    wrapper = create_mofsl_wrapper("UAT")
    
    # Test with dummy data (would fail in real scenario without valid token)
    try:
        # These would require valid auth tokens
        print("Testing method signatures...")
        
        # Check method existence
        assert hasattr(wrapper, 'get_positions'), "get_positions method missing"
        assert hasattr(wrapper, 'get_holdings'), "get_holdings method missing"
        assert hasattr(wrapper, 'search_instruments'), "search_instruments method missing"
        assert hasattr(wrapper, 'get_client_profile'), "get_client_profile method missing"
        assert hasattr(wrapper, 'get_portfolio_summary'), "get_portfolio_summary method missing"
        
        print("✅ All data fetching methods are present")
        
        # Test exchange validation
        try:
            await wrapper.search_instruments("dummy_token", "INVALID_EXCHANGE")
            print("❌ Exchange validation failed")
        except ValueError as e:
            if "Invalid exchange" in str(e):
                print("✅ Exchange validation working")
            else:
                print(f"❌ Unexpected validation error: {e}")
        
    except Exception as e:
        print(f"❌ Error in data fetching test: {e}")
    
    print("Data fetching test completed")

async def test_order_management():
    """
    Test order management functionality (for development only)
    """
    print("=== Testing MOFSL Order Management ===")
    
    wrapper = create_mofsl_wrapper("UAT")
    
    try:
        # Check method existence
        assert hasattr(wrapper, 'place_order'), "place_order method missing"
        assert hasattr(wrapper, 'modify_order'), "modify_order method missing"
        assert hasattr(wrapper, 'cancel_order'), "cancel_order method missing"
        assert hasattr(wrapper, 'get_order_status'), "get_order_status method missing"
        assert hasattr(wrapper, 'get_order_book'), "get_order_book method missing"
        
        print("✅ All order management methods are present")
        
        # Test validation methods
        assert hasattr(wrapper, '_validate_order_details'), "Order validation method missing"
        assert hasattr(wrapper, '_map_order_to_mofsl_payload'), "Payload mapping method missing"
        assert hasattr(wrapper, '_extract_order_id'), "Order ID extraction method missing"
        assert hasattr(wrapper, '_check_order_operation_success'), "Success check method missing"
        
        print("✅ All helper methods are present")
        
        # Test order type mappings
        test_payload = wrapper._map_order_to_mofsl_payload(
            type('MockOrder', (), {
                'token_id': 123,
                'transaction_type': 'BUY',
                'order_type': 'LMT',
                'product_type': 'MIS',
                'quantity': 10,
                'price': 100.50,
                'trigger_price': None,
                'disclosed_quantity': 0,
                'validity': 'DAY',
                'exchange': 'NSE',
                'remarks': 'Test order'
            })(),
            'TEST001'
        )
        
        expected_fields = ['clientcode', 'symboltoken', 'transactiontype', 'ordertype', 'producttype', 'quantity', 'exchange', 'validity', 'price']
        for field in expected_fields:
            assert field in test_payload, f"Missing field in payload: {field}"
        
        print("✅ Order payload mapping working correctly")
        
    except Exception as e:
        print(f"❌ Error in order management test: {e}")
    
    print("Order management test completed")

if __name__ == "__main__":
    # Run tests if script is executed directly
    asyncio.run(test_authentication())
    print()
    asyncio.run(test_data_fetching())
    print()
    asyncio.run(test_order_management())