import os
import time
import asyncio
from functools import wraps
from typing import Any, Awaitable, Callable, List

import httpx

# Import bucket classes for rate limiting
from pyrate_limiter import Limiter, Rate, Duration, SQLiteBucket, InMemoryBucket


# -------------------------
# 1. Configuration (Module-level, shared resources)
# -------------------------

# Global rate: 60 requests per minute
REQUEST_RATE = Rate(60, Duration.MINUTE)

# SQLite DB path for persistence - will be set by the plugin instance
# Default to local data directory for module-level initialization
_DEFAULT_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_DATA_DIR = _DEFAULT_DATA_DIR
SQLITE_DB_PATH = os.path.join(_DATA_DIR, "pyrate_limiter_global.sqlite")
os.makedirs(_DATA_DIR, exist_ok=True)

# Key for all calls (all functions using this key share the same global limit)
LIMIT_ITEM_NAME = "RanobeDB_api_call"

# -------------------------
# 2. Initialize Global Limiter (Using idiomatic process-safe initialization)
# -------------------------

def _init_limiter(data_dir: str | None = None):
    """Initialize or reinitialize the global rate limiter with a new data directory."""
    global GLOBAL_LIMITER, SQLITE_DB_PATH, _DATA_DIR
    
    if data_dir:
        _DATA_DIR = data_dir
        SQLITE_DB_PATH = os.path.join(_DATA_DIR, "pyrate_limiter_global.sqlite")
        os.makedirs(_DATA_DIR, exist_ok=True)
    
    try:
        # Use init_from_file to properly handle file locking for multi-process safety
        # CRITICAL: use_file_lock=True enables cross-process coordination via FileLock
        sqlite_bucket = SQLiteBucket.init_from_file(
            rates=[REQUEST_RATE],
            table="rate_limiter",
            db_path=SQLITE_DB_PATH,
            create_new_table=True,
            use_file_lock=True,  # CRITICAL: Enables process-safe concurrent access
        )

        GLOBAL_LIMITER = Limiter(
            sqlite_bucket,
            raise_when_fail=False,  # Don't raise, use delay mechanism instead
            max_delay=Duration.HOUR,  # Wait indefinitely until slot is available
        )
        print(f"[INFO] Rate Limiter initialized with SQLite backend at {SQLITE_DB_PATH}")
        print(f"[INFO] File locking enabled for multi-process safety")

    except ImportError as e:
        print(f"[ERROR] filelock package required for multi-process rate limiting: {e}")
        print(f"[ERROR] Install with: pip install filelock")
        raise
    except Exception as e:
        print(f"[WARN] SQLite limiter init failed, falling back to in-memory: {e}")
        # Fallback to a non-persistent, in-memory limiter (Warning: Not global across processes!)
        memory_bucket = InMemoryBucket([REQUEST_RATE])
        GLOBAL_LIMITER = Limiter(
            memory_bucket,
            raise_when_fail=False,
            max_delay=Duration.HOUR,
        )

# Initialize with default directory
_init_limiter()

# -------------------------
# 3. Async rate-limit decorator (Using precise try_acquire_async)
# -------------------------


def async_rate_limit_pause(
    func: Callable[..., Awaitable[Any]],
) -> Callable[..., Awaitable[Any]]:
    """
    Async decorator: globally rate-limits the decorated function using the Leaky Bucket algorithm.
    Pauses ASYNCHRONOUSLY (await asyncio.sleep) until a slot is available,
    avoiding blocking the main event loop.

    Uses the limiter's built-in async delay mechanism (try_acquire_async) which:
    - Precisely calculates wait time based on bucket state
    - Efficiently waits using asyncio.sleep (non-blocking)
    - Respects max_delay setting (waits indefinitely if None)
    - Works correctly with file-locked SQLite for multi-process coordination
    """

    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        # Use the library's async acquire method which handles delays properly
        # This will automatically wait (non-blocking) if rate limit is exceeded
        max_retries = 6
        retry_delay = 1.0  # seconds

        for attempt in range(max_retries):
            try:
                acquired = await GLOBAL_LIMITER.try_acquire_async(LIMIT_ITEM_NAME)

                if acquired:
                    return await func(*args, **kwargs)

                if attempt < max_retries - 1:
                    print(
                        f"[WARN] Rate limit exceeded, retrying in {retry_delay} seconds... (Attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
            except Exception as e:
                print(f"[ERROR] Exception during rate limit acquire: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    raise

        raise RuntimeError(
            f"Failed to acquire rate limit slot after {max_retries} attempts"
        )

    return wrapper


# -------------------------
# 4. Core Async API Call Function
# -------------------------


@async_rate_limit_pause
async def fetch_endpoint(endpoint: str, client: httpx.AsyncClient) -> dict:
    """
    Makes an async GET request to an external API endpoint,
    respecting the global rate limit by pausing if necessary.

    NOTE: The httpx.AsyncClient must be managed (created/closed) by the caller
    (e.g., in a context manager) for efficiency.
    """
    url = f"https://api.external-service.com/{endpoint}"
    print(f"[{time.strftime('%H:%M:%S')}] Attempting API call to {url}...")

    try:
        response = await client.get(url, timeout=10.0)
        response.raise_for_status()  # Raises HTTPStatusError for 4xx/5xx responses
        data = response.json()
        print(f"[{time.strftime('%H:%M:%S')}] ✅ Success: {url}")
        return data

    except httpx.RequestError as e:
        # Catches network errors, DNS failures, timeouts, etc.
        print(f"[{time.strftime('%H:%M:%S')}] ❌ Request error (Network/Timeout): {e}")
        return {"status": "error", "message": f"Network/Request Error: {str(e)}"}
    except httpx.HTTPStatusError as e:
        # Catches bad HTTP status codes (4xx/5xx)
        print(f"[{time.strftime('%H:%M:%S')}] ❌ HTTP error: {e}")
        return {
            "status": "error",
            "message": f"HTTP Error {e.response.status_code}: {str(e)}",
        }


# -------------------------
# 5. Convenience wrapper for concurrent calls
# -------------------------


async def fetch_multiple_endpoints(endpoints: List[str]) -> List[dict]:
    """
    Fetch multiple endpoints concurrently while managing a single httpx client
    and respecting the global limit.
    """
    # Best practice: manage client lifespan using async with
    async with httpx.AsyncClient() as client:
        # Create tasks, which will pause themselves via the decorator if limited
        tasks = [fetch_endpoint(ep, client) for ep in endpoints]

        # Run them concurrently, allowing the rate limiter to manage the flow
        results = await asyncio.gather(
            *tasks, return_exceptions=False
        )  ## TODO: Handle exceptions if needed
        return results


# -------------------------
# 6. Optional sync wrapper for Celery (or other sync contexts)
# -------------------------


def fetch_endpoint_sync(endpoint: str) -> dict:
    """
    Synchronous wrapper for calling the async rate-limited function.
    Use this inside standard Celery tasks or other synchronous code.
    """
    # This library is often required when calling asyncio.run() inside an
    # environment that already runs an event loop (like some Celery setups).
    try:
        import nest_asyncio

        nest_asyncio.apply()
    except ImportError:
        # If running in a clean environment, nest_asyncio isn't needed
        pass

    # We call the fetch_multiple_endpoints wrapper for full client management
    # and then extract the result of the single endpoint.
    return asyncio.run(fetch_multiple_endpoints([endpoint]))[0]


# -------------------------
# Usage Example (Async)
# -------------------------

if __name__ == "__main__":
    print(
        f"--- Global ASYNC Rate Limiter Test ({REQUEST_RATE.limit} req / {REQUEST_RATE.interval} sec) ---"
    )

    async def test():
        # Create 10 endpoints to hit the limiter immediately (60/min = 1/sec)
        endpoints = [f"item/{i+1}" for i in range(10)]
        start_time = time.time()

        results = await fetch_multiple_endpoints(endpoints)

        end_time = time.time()
        print("\n--- Test Results ---")
        for res in results:
            # Simple print of the result structure
            print(
                f"Status: {res.get('status')}, Message: {res.get('message', 'No message')[:40]}..."
            )

        print(
            f"\nTotal time for 10 concurrent requests: {end_time - start_time:.2f} seconds."
        )
        print(
            "This time should be significantly longer than the requests' natural latency (0.1s) due to the rate limit."
        )

    asyncio.run(test())
