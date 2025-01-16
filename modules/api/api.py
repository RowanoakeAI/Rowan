from fastapi import FastAPI, HTTPException, Depends, Security, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import uvicorn
import threading
import uuid
import time
from collections import defaultdict
import jwt
from pydantic import BaseModel, Field
import asyncio
from core.module_manager import ModuleInterface
from core.personal_memory import InteractionContext, InteractionSource
from utils.logger import setup_logger
from config.api_config import APIConfig

class RateLimiter:
    def __init__(self, requests_per_minute: int = 60, window_seconds: int = 60, burst_limit: int = 10):
        self.requests_per_minute = requests_per_minute
        self.window_seconds = window_seconds
        self.burst_limit = burst_limit
        self.requests = defaultdict(list)
        self.lock = threading.Lock()
        self.logger = setup_logger(__name__)
        
        # Start cleanup task
        self.cleanup_task = asyncio.create_task(self._cleanup_old_requests())

    async def _cleanup_old_requests(self):
        while True:
            try:
                await asyncio.sleep(60)  # Run cleanup every minute
                now = time.time()
                with self.lock:
                    for api_key in list(self.requests.keys()):
                        self.requests[api_key] = [req_time for req_time in self.requests[api_key]
                                                if req_time > now - self.window_seconds]
                        if not self.requests[api_key]:
                            del self.requests[api_key]
            except Exception as e:
                self.logger.error(f"Error in cleanup task: {str(e)}")

    def get_limit_status(self, api_key: str) -> Dict[str, int]:
        """Get current rate limit status for an API key"""
        now = time.time()
        with self.lock:
            current_requests = [r for r in self.requests[api_key] 
                              if r > now - self.window_seconds]
            return {
                "current_requests": len(current_requests),
                "limit": self.requests_per_minute,
                "burst_remaining": self.burst_limit - max(0, len(current_requests) - self.requests_per_minute),
                "reset_in": int(self.window_seconds - (now - min(current_requests))) if current_requests else 0
            }

    async def check(self, api_key: str):
        now = time.time()
        
        with self.lock:
            # Remove old requests
            self.requests[api_key] = [req_time for req_time in self.requests[api_key]
                                    if req_time > now - self.window_seconds]
            
            # Check regular rate limit
            if len(self.requests[api_key]) >= self.requests_per_minute:
                # Check burst allowance
                oldest_request = min(self.requests[api_key]) if self.requests[api_key] else now
                if len(self.requests[api_key]) >= self.requests_per_minute + self.burst_limit:
                    retry_after = max(1, int(self.window_seconds - (now - oldest_request)))
                    self.logger.warning(f"Rate limit exceeded for API key: {api_key}")
                    raise HTTPException(
                        status_code=429,
                        detail={
                            "error": "Rate limit exceeded",
                            "limit": self.requests_per_minute,
                            "burst_limit": self.burst_limit,
                            "current_requests": len(self.requests[api_key]),
                            "retry_after": retry_after
                        },
                        headers={
                            "Retry-After": str(retry_after),
                            "X-RateLimit-Limit": str(self.requests_per_minute),
                            "X-RateLimit-Remaining": "0",
                            "X-RateLimit-Reset": str(int(oldest_request + self.window_seconds))
                        }
                    )
            
            self.requests[api_key].append(now)
            
            # Add rate limit headers
            remaining = self.requests_per_minute - len(self.requests[api_key])
            return {
                "X-RateLimit-Limit": str(self.requests_per_minute),
                "X-RateLimit-Remaining": str(max(0, remaining)),
                "X-RateLimit-Reset": str(int(now + self.window_seconds))
            }

class APIKeyValidator:
    def __init__(self, cache_ttl: int = 300):  # 5 minute cache
        self._cache: Dict[str, float] = {}
        self.cache_ttl = cache_ttl
        self.lock = threading.Lock()

    async def validate(self, api_key: str) -> str:
        now = time.time()
        
        # Check cache first
        with self.lock:
            if api_key in self._cache and self._cache[api_key] > now:
                return api_key

        # Validate key if not in cache
        if api_key not in APIConfig.API_KEYS:
            raise HTTPException(
                status_code=401,
                detail="Invalid API key"
            )

        # Get key data
        key_data = APIConfig.API_KEYS[api_key]

        # Check expiration if configured
        if isinstance(key_data, dict) and key_data.get('expires_at'):
            if datetime.fromisoformat(key_data['expires_at']) < datetime.utcnow():
                raise HTTPException(
                    status_code=401,
                    detail="Expired API key"
                )

        # Cache valid key
        with self.lock:
            self._cache[api_key] = now + self.cache_ttl
            
        return api_key

api_key_validator = APIKeyValidator()
api_key_header = APIKeyHeader(name="X-API-Key")

async def validate_api_key(api_key: str = Security(api_key_header)) -> str:
    return await api_key_validator.validate(api_key)

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    context_type: Optional[str] = "casual"
    source: Optional[str] = "api"
    metadata: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    response: str
    timestamp: datetime
    request_id: str
    metadata: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    timestamp: datetime
    request_id: str

class RowanAPI(FastAPI):
    def __init__(self, rowan_assistant=None):
        super().__init__(
            title="Rowan API",
            description="REST API for Rowan Assistant",
            version="1.0.0"
        )
        self.rowan = rowan_assistant
        self.rate_limiter = RateLimiter()
        self.setup_middleware()
        self.setup_routes()

    def setup_middleware(self):
        """Configure API middleware"""
        self.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def setup_routes(self):
        """Setup API endpoints"""
        @self.post("/chat", response_model=ChatResponse)
        async def chat(
            request: ChatRequest,
            api_key: str = Depends(validate_api_key)
        ):

            await self.rate_limiter.check(api_key)
            
            if not self.rowan:
                raise HTTPException(status_code=503, detail="Rowan not initialized")

            try:
                response = self.rowan.chat(
                    request.message,
                    context_type=InteractionContext[request.context_type.upper()],
                    source=InteractionSource.API,
                )
                
                return ChatResponse(
                    response=response,
                    timestamp=datetime.utcnow(),
                    request_id=str(uuid.uuid4()),
                    metadata=request.metadata
                )

            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.get("/status")
        async def status(api_key: str = Depends(validate_api_key)):
            return {
                "status": "online",
                "timestamp": datetime.utcnow().isoformat()
            }

class ApiModule(ModuleInterface):
    """Web API interface for Rowan"""
    
    def __init__(self):
        self.logger = setup_logger(__name__)
        self.port = 7692
        self.should_run = True
        self.server_thread = None
        self.app = None
        self.connections = set()
        self.shutdown_event = asyncio.Event()

    async def _connection_handler(self, reader, writer):
        """Handle individual connections"""
        self.connections.add(writer)
        try:
            while self.should_run:
                try:
                    data = await asyncio.wait_for(reader.read(1024), timeout=5.0)
                    if not data:
                        break
                    # Process data...
                except (asyncio.TimeoutError, ConnectionResetError):
                    break
        finally:
            self.connections.remove(writer)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception as e:
                self.logger.debug(f"Error closing connection: {e}")

    async def _graceful_shutdown(self):
        """Gracefully shutdown server and connections"""
        self.should_run = False
        self.shutdown_event.set()
        
        # Close all active connections
        for writer in self.connections:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception as e:
                self.logger.debug(f"Error closing connection: {e}")
        
        # Wait for connections to close
        if self.connections:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*[writer.wait_closed() for writer in self.connections]),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                self.logger.warning("Timeout waiting for connections to close")

    def _run_server(self):
        """Run the FastAPI server with proper error handling"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            config = uvicorn.Config(
                app=self.app,
                host="0.0.0.0", 
                port=self.port,
                loop=loop,
                timeout_keep_alive=30,
                limit_concurrency=100
            )
            server = uvicorn.Server(config)
            
            # Handle signals
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, lambda: asyncio.create_task(self._graceful_shutdown()))
            
            loop.run_until_complete(server.serve())
            
        except Exception as e:
            self.logger.error(f"API server error: {str(e)}")
        finally:
            try:
                loop.run_until_complete(self._graceful_shutdown())
            except Exception as e:
                self.logger.error(f"Error during shutdown: {e}")
            loop.close()

    def shutdown(self) -> None:
        """Shutdown API server with proper cleanup"""
        try:
            self.should_run = False
            if self.server_thread:
                # Give time for graceful shutdown
                self.server_thread.join(timeout=10.0)
                if self.server_thread.is_alive():
                    self.logger.warning("Server thread did not terminate gracefully")
            
            self.logger.info("API module shut down")
            
        except Exception as e:
            self.logger.error(f"Error during API shutdown: {str(e)}")