"""
Advanced Connection Pooling and Circuit Breaker for CRM Integrations
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from contextlib import asynccontextmanager
from collections import defaultdict, deque
import aiohttp
import redis.asyncio as aioredis
from django.conf import settings
from django.core.cache import cache
from ingestion.base.exceptions import ConnectionException, RateLimitException

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking requests
    HALF_OPEN = "half_open"  # Testing if service is back

@dataclass
class ConnectionStats:
    """Connection statistics tracking"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0
    last_failure_time: Optional[datetime] = None
    consecutive_failures: int = 0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests
    
    @property
    def failure_rate(self) -> float:
        """Calculate failure rate"""
        return 1.0 - self.success_rate

@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    success_threshold: int = 3  # for half-open state
    timeout: int = 30  # request timeout
    
class CircuitBreaker:
    """Circuit breaker implementation"""
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.stats = ConnectionStats()
        self.last_failure_time = None
        self.half_open_requests = 0
        self.lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if not await self.can_execute():
            raise ConnectionException(f"Circuit breaker {self.name} is OPEN")
        
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            await self.record_success(time.time() - start_time)
            return result
        except Exception as e:
            await self.record_failure(time.time() - start_time)
            raise
    
    async def can_execute(self) -> bool:
        """Check if request can be executed"""
        async with self.lock:
            if self.state == CircuitState.CLOSED:
                return True
            elif self.state == CircuitState.OPEN:
                if self.should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_requests = 0
                    return True
                return False
            else:  # HALF_OPEN
                return self.half_open_requests < self.config.success_threshold
    
    def should_attempt_reset(self) -> bool:
        """Check if circuit should attempt reset"""
        if self.last_failure_time is None:
            return False
        
        time_since_failure = time.time() - self.last_failure_time.timestamp()
        return time_since_failure >= self.config.recovery_timeout
    
    async def record_success(self, response_time: float):
        """Record successful request"""
        async with self.lock:
            self.stats.total_requests += 1
            self.stats.successful_requests += 1
            self.stats.consecutive_failures = 0
            
            # Update average response time
            self.update_avg_response_time(response_time)
            
            # Handle state transitions
            if self.state == CircuitState.HALF_OPEN:
                self.half_open_requests += 1
                if self.half_open_requests >= self.config.success_threshold:
                    self.state = CircuitState.CLOSED
                    logger.info(f"Circuit breaker {self.name} reset to CLOSED")
    
    async def record_failure(self, response_time: float):
        """Record failed request"""
        async with self.lock:
            self.stats.total_requests += 1
            self.stats.failed_requests += 1
            self.stats.consecutive_failures += 1
            self.stats.last_failure_time = datetime.now()
            self.last_failure_time = datetime.now()
            
            # Update average response time
            self.update_avg_response_time(response_time)
            
            # Check if circuit should open
            if (self.state == CircuitState.CLOSED and 
                self.stats.consecutive_failures >= self.config.failure_threshold):
                self.state = CircuitState.OPEN
                logger.warning(f"Circuit breaker {self.name} opened due to {self.stats.consecutive_failures} consecutive failures")
            elif self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                logger.warning(f"Circuit breaker {self.name} reopened after failure in half-open state")
    
    def update_avg_response_time(self, response_time: float):
        """Update average response time"""
        if self.stats.avg_response_time == 0:
            self.stats.avg_response_time = response_time
        else:
            # Exponential moving average
            self.stats.avg_response_time = (self.stats.avg_response_time * 0.9) + (response_time * 0.1)
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state"""
        return {
            'name': self.name,
            'state': self.state.value,
            'stats': {
                'total_requests': self.stats.total_requests,
                'successful_requests': self.stats.successful_requests,
                'failed_requests': self.stats.failed_requests,
                'success_rate': self.stats.success_rate,
                'failure_rate': self.stats.failure_rate,
                'avg_response_time': self.stats.avg_response_time,
                'consecutive_failures': self.stats.consecutive_failures
            }
        }

class ConnectionPool:
    """Advanced connection pool with intelligent management"""
    
    def __init__(self, name: str, max_connections: int = 100, 
                 min_connections: int = 10, idle_timeout: int = 300):
        self.name = name
        self.max_connections = max_connections
        self.min_connections = min_connections
        self.idle_timeout = idle_timeout
        
        self.active_connections = []
        self.idle_connections = deque()
        self.connection_stats = defaultdict(ConnectionStats)
        self.creation_time = {}
        self.last_used = {}
        self.lock = asyncio.Lock()
        
        # Background tasks
        self.cleanup_task = None
        self.health_check_task = None
        
    async def start(self):
        """Start connection pool"""
        # Create minimum connections
        for _ in range(self.min_connections):
            conn = await self.create_connection()
            self.idle_connections.append(conn)
        
        # Start background tasks
        self.cleanup_task = asyncio.create_task(self.cleanup_idle_connections())
        self.health_check_task = asyncio.create_task(self.health_check_connections())
        
        logger.info(f"Connection pool {self.name} started with {len(self.idle_connections)} connections")
    
    async def stop(self):
        """Stop connection pool"""
        if self.cleanup_task:
            self.cleanup_task.cancel()
        if self.health_check_task:
            self.health_check_task.cancel()
        
        # Close all connections
        async with self.lock:
            for conn in self.active_connections + list(self.idle_connections):
                await self.close_connection(conn)
            
            self.active_connections.clear()
            self.idle_connections.clear()
        
        logger.info(f"Connection pool {self.name} stopped")

    async def close(self):
        """Alias to stop() for cleanup compatibility"""
        await self.stop()
    
    @asynccontextmanager
    async def get_connection(self):
        """Get connection from pool"""
        conn = None
        try:
            conn = await self.acquire_connection()
            yield conn
        finally:
            if conn:
                await self.release_connection(conn)
    
    async def acquire_connection(self):
        """Acquire connection from pool"""
        async with self.lock:
            # Try to get from idle connections
            if self.idle_connections:
                conn = self.idle_connections.popleft()
                
                # Check if connection is still valid
                if await self.is_connection_valid(conn):
                    self.active_connections.append(conn)
                    self.last_used[id(conn)] = time.time()
                    return conn
                else:
                    # Connection is invalid, close it
                    await self.close_connection(conn)
            
            # Create new connection if possible
            if len(self.active_connections) < self.max_connections:
                conn = await self.create_connection()
                self.active_connections.append(conn)
                self.last_used[id(conn)] = time.time()
                return conn
            
            # Pool is full, wait for available connection
            raise ConnectionException(f"Connection pool {self.name} is exhausted")
    
    async def release_connection(self, conn):
        """Release connection back to pool"""
        async with self.lock:
            if conn in self.active_connections:
                self.active_connections.remove(conn)
                
                # Check if connection is still healthy
                if await self.is_connection_valid(conn):
                    self.idle_connections.append(conn)
                    self.last_used[id(conn)] = time.time()
                else:
                    await self.close_connection(conn)
    
    async def create_connection(self):
        """Create new connection - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement create_connection")
    
    async def close_connection(self, conn):
        """Close connection - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement close_connection")
    
    async def is_connection_valid(self, conn) -> bool:
        """Check if connection is valid - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement is_connection_valid")
    
    async def cleanup_idle_connections(self):
        """Cleanup idle connections periodically"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                async with self.lock:
                    current_time = time.time()
                    connections_to_remove = []
                    
                    for conn in list(self.idle_connections):
                        conn_id = id(conn)
                        if (conn_id in self.last_used and 
                            current_time - self.last_used[conn_id] > self.idle_timeout):
                            connections_to_remove.append(conn)
                    
                    for conn in connections_to_remove:
                        self.idle_connections.remove(conn)
                        await self.close_connection(conn)
                        if id(conn) in self.last_used:
                            del self.last_used[id(conn)]
                    
                    if connections_to_remove:
                        logger.info(f"Cleaned up {len(connections_to_remove)} idle connections from pool {self.name}")
            
            except Exception as e:
                logger.error(f"Error in connection cleanup: {e}")
    
    async def health_check_connections(self):
        """Perform health checks on connections"""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                async with self.lock:
                    unhealthy_connections = []
                    
                    for conn in list(self.idle_connections):
                        if not await self.is_connection_valid(conn):
                            unhealthy_connections.append(conn)
                    
                    for conn in unhealthy_connections:
                        self.idle_connections.remove(conn)
                        await self.close_connection(conn)
                        if id(conn) in self.last_used:
                            del self.last_used[id(conn)]
                    
                    if unhealthy_connections:
                        logger.warning(f"Removed {len(unhealthy_connections)} unhealthy connections from pool {self.name}")
                        
                        # Create replacement connections if needed
                        current_total = len(self.active_connections) + len(self.idle_connections)
                        if current_total < self.min_connections:
                            needed = self.min_connections - current_total
                            for _ in range(needed):
                                try:
                                    new_conn = await self.create_connection()
                                    self.idle_connections.append(new_conn)
                                except Exception as e:
                                    logger.error(f"Failed to create replacement connection: {e}")
                                    break
            
            except Exception as e:
                logger.error(f"Error in connection health check: {e}")
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        return {
            'name': self.name,
            'max_connections': self.max_connections,
            'min_connections': self.min_connections,
            'active_connections': len(self.active_connections),
            'idle_connections': len(self.idle_connections),
            'total_connections': len(self.active_connections) + len(self.idle_connections),
            'utilization': len(self.active_connections) / self.max_connections
        }

class HTTPConnectionPool(ConnectionPool):
    """HTTP connection pool implementation"""
    
    def __init__(self, name: str, base_url: str, **kwargs):
        super().__init__(name, **kwargs)
        self.base_url = base_url
        self.session_kwargs = kwargs.get('session_kwargs', {})
    
    async def create_connection(self):
        """Create new HTTP connection"""
        connector = aiohttp.TCPConnector(
            limit=self.max_connections,
            limit_per_host=self.max_connections,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        
        session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=30),
            **self.session_kwargs
        )
        
        conn_id = id(session)
        self.creation_time[conn_id] = time.time()
        
        logger.debug(f"Created HTTP connection {conn_id} for pool {self.name}")
        return session
    
    async def close_connection(self, conn):
        """Close HTTP connection"""
        try:
            if not conn.closed:
                await conn.close()
            
            conn_id = id(conn)
            if conn_id in self.creation_time:
                del self.creation_time[conn_id]
            
            logger.debug(f"Closed HTTP connection {conn_id} for pool {self.name}")
        except Exception as e:
            logger.error(f"Error closing HTTP connection: {e}")
    
    async def is_connection_valid(self, conn) -> bool:
        """Check if HTTP connection is valid"""
        try:
            return not conn.closed
        except Exception:
            return False
    
    async def get_session(self):
        """Get a session from the connection pool (backward compatibility method)"""
        return await self.acquire_connection()

class DatabaseConnectionPool(ConnectionPool):
    """Database connection pool implementation"""
    
    def __init__(self, name: str, database_url: str, **kwargs):
        super().__init__(name, **kwargs)
        self.database_url = database_url
        self.connection_kwargs = kwargs.get('connection_kwargs', {})
    
    async def create_connection(self):
        """Create new database connection"""
        # This would be implemented based on your database type
        # For example, using asyncpg for PostgreSQL
        import asyncpg
        
        conn = await asyncpg.connect(self.database_url, **self.connection_kwargs)
        
        conn_id = id(conn)
        self.creation_time[conn_id] = time.time()
        
        logger.debug(f"Created database connection {conn_id} for pool {self.name}")
        return conn
    
    async def close_connection(self, conn):
        """Close database connection"""
        try:
            await conn.close()
            
            conn_id = id(conn)
            if conn_id in self.creation_time:
                del self.creation_time[conn_id]
            
            logger.debug(f"Closed database connection {conn_id} for pool {self.name}")
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")
    
    async def is_connection_valid(self, conn) -> bool:
        """Check if database connection is valid"""
        try:
            await conn.fetchval("SELECT 1")
            return True
        except Exception:
            return False

class RedisConnectionPool(ConnectionPool):
    """Redis connection pool implementation"""
    
    def __init__(self, name: str, redis_url: str, **kwargs):
        super().__init__(name, **kwargs)
        self.redis_url = redis_url
        self.connection_kwargs = kwargs.get('connection_kwargs', {})
    
    async def create_connection(self):
        """Create new Redis connection"""
        conn = await aioredis.from_url(self.redis_url, **self.connection_kwargs)
        
        conn_id = id(conn)
        self.creation_time[conn_id] = time.time()
        
        logger.debug(f"Created Redis connection {conn_id} for pool {self.name}")
        return conn
    
    async def close_connection(self, conn):
        """Close Redis connection"""
        try:
            await conn.close()
            
            conn_id = id(conn)
            if conn_id in self.creation_time:
                del self.creation_time[conn_id]
            
            logger.debug(f"Closed Redis connection {conn_id} for pool {self.name}")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")
    
    async def is_connection_valid(self, conn) -> bool:
        """Check if Redis connection is valid"""
        try:
            await conn.ping()
            return True
        except Exception:
            return False

class ConnectionManager:
    """Central connection manager"""
    
    def __init__(self):
        self.pools = {}
        self.circuit_breakers = {}
        self.default_circuit_config = CircuitBreakerConfig()
    
    def create_http_pool(self, name: str, base_url: str, **kwargs) -> HTTPConnectionPool:
        """Create HTTP connection pool"""
        circuit_config = kwargs.pop('circuit_config', self.default_circuit_config)
        pool = HTTPConnectionPool(name, base_url, **kwargs)
        self.pools[name] = pool
        self.circuit_breakers[name] = CircuitBreaker(name, circuit_config)
        return pool
    
    def create_database_pool(self, name: str, database_url: str, **kwargs) -> DatabaseConnectionPool:
        """Create database connection pool"""
        circuit_config = kwargs.pop('circuit_config', self.default_circuit_config)
        pool = DatabaseConnectionPool(name, database_url, **kwargs)
        self.pools[name] = pool
        self.circuit_breakers[name] = CircuitBreaker(name, circuit_config)
        return pool
    
    def create_redis_pool(self, name: str, redis_url: str, **kwargs) -> RedisConnectionPool:
        """Create Redis connection pool"""
        circuit_config = kwargs.pop('circuit_config', self.default_circuit_config)
        pool = RedisConnectionPool(name, redis_url, **kwargs)
        self.pools[name] = pool
        self.circuit_breakers[name] = CircuitBreaker(name, circuit_config)
        return pool
    
    def get_pool(self, name: str) -> ConnectionPool:
        """Get connection pool by name"""
        return self.pools.get(name)
    
    def get_circuit_breaker(self, name: str) -> CircuitBreaker:
        """Get circuit breaker by name"""
        return self.circuit_breakers.get(name)
    
    @asynccontextmanager
    async def get_connection(self, pool_name: str):
        """Get connection with circuit breaker protection"""
        pool = self.get_pool(pool_name)
        circuit_breaker = self.get_circuit_breaker(pool_name)
        
        if not pool:
            raise ConnectionException(f"Connection pool {pool_name} not found")
        
        if not circuit_breaker:
            raise ConnectionException(f"Circuit breaker {pool_name} not found")
        
        # Use circuit breaker to get connection
        async with circuit_breaker.call(pool.get_connection) as conn:
            yield conn
    
    async def start_all_pools(self):
        """Start all connection pools"""
        for name, pool in self.pools.items():
            try:
                await pool.start()
                logger.info(f"Started connection pool: {name}")
            except Exception as e:
                logger.error(f"Failed to start connection pool {name}: {e}")
    
    async def stop_all_pools(self):
        """Stop all connection pools"""
        for name, pool in self.pools.items():
            try:
                await pool.stop()
                logger.info(f"Stopped connection pool: {name}")
            except Exception as e:
                logger.error(f"Failed to stop connection pool {name}: {e}")
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all pools and circuit breakers"""
        stats = {
            'pools': {},
            'circuit_breakers': {}
        }
        
        for name, pool in self.pools.items():
            stats['pools'][name] = pool.get_pool_stats()
        
        for name, circuit_breaker in self.circuit_breakers.items():
            stats['circuit_breakers'][name] = circuit_breaker.get_state()
        
        return stats

# Global connection manager
connection_manager = ConnectionManager()

# Initialize connection pools for the application
async def initialize_connection_pools():
    """Initialize connection pools for the application"""
    
    # Only initialize if Django settings are available
    try:
        from django.conf import settings
    except ImportError:
        logger.warning("Django settings not available, skipping connection pool initialization")
        return
    
    # HTTP pools for different CRM APIs
    connection_manager.create_http_pool(
        'hubspot_api',
        'https://api.hubapi.com',
        max_connections=50,
        min_connections=5,
        circuit_config=CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60,
            timeout=30
        )
    )
    
    connection_manager.create_http_pool(
        'genius_api',
        'https://api.genius.com',
        max_connections=30,
        min_connections=3,
        circuit_config=CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=45,
            timeout=25
        )
    )
    
    # Database pool
    try:
        if hasattr(settings, 'DATABASE_URL') and settings.DATABASE_URL:
            connection_manager.create_database_pool(
                'main_database',
                settings.DATABASE_URL,
                max_connections=20,
                min_connections=5,
                circuit_config=CircuitBreakerConfig(
                    failure_threshold=10,
                    recovery_timeout=30,
                    timeout=60
                )
            )
    except Exception as e:
        logger.warning(f"Failed to create database pool: {e}")
    
    # Redis pool
    try:
        if hasattr(settings, 'REDIS_URL') and settings.REDIS_URL:
            connection_manager.create_redis_pool(
                'cache_redis',
                settings.REDIS_URL,
                max_connections=15,
                min_connections=3,
                circuit_config=CircuitBreakerConfig(
                    failure_threshold=5,
                    recovery_timeout=30,
                    timeout=10
                )
            )
    except Exception as e:
        logger.warning(f"Failed to create Redis pool: {e}")
    
    # Start all pools
    try:
        await connection_manager.start_all_pools()
        logger.info("Connection pools initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to start some connection pools: {e}")

# Context manager for easy usage
@asynccontextmanager
async def get_api_connection(api_name: str):
    """Get API connection with automatic management"""
    async with connection_manager.get_connection(f"{api_name}_api") as conn:
        yield conn

# Example usage functions
async def make_hubspot_request(endpoint: str, method: str = 'GET', **kwargs):
    """Make HubSpot API request using connection pool"""
    async with get_api_connection('hubspot') as session:
        async with session.request(method, endpoint, **kwargs) as response:
            return await response.json()

async def make_genius_request(endpoint: str, method: str = 'GET', **kwargs):
    """Make Genius API request using connection pool"""
    async with get_api_connection('genius') as session:
        async with session.request(method, endpoint, **kwargs) as response:
            return await response.json()

# Health check endpoint
async def get_connection_health():
    """Get health status of all connections"""
    stats = connection_manager.get_all_stats()
    
    health_status = {
        'overall_health': 'healthy',
        'pools': {},
        'circuit_breakers': {}
    }
    
    # Check pool health
    for name, pool_stats in stats['pools'].items():
        utilization = pool_stats['utilization']
        if utilization > 0.9:
            health_status['pools'][name] = 'warning'
        elif utilization > 0.95:
            health_status['pools'][name] = 'critical'
        else:
            health_status['pools'][name] = 'healthy'
    
    # Check circuit breaker health
    for name, cb_stats in stats['circuit_breakers'].items():
        state = cb_stats['state']
        if state == 'open':
            health_status['circuit_breakers'][name] = 'critical'
        elif state == 'half_open':
            health_status['circuit_breakers'][name] = 'warning'
        else:
            health_status['circuit_breakers'][name] = 'healthy'
    
    # Determine overall health
    if any(status == 'critical' for status in health_status['pools'].values() + health_status['circuit_breakers'].values()):
        health_status['overall_health'] = 'critical'
    elif any(status == 'warning' for status in health_status['pools'].values() + health_status['circuit_breakers'].values()):
        health_status['overall_health'] = 'warning'
    
    return health_status
