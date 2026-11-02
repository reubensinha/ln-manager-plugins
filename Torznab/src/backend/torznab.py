from typing import Any, Dict, List
from backend.core.plugins.base import BasePlugin
from backend.core.plugins.indexer import IndexerPlugin
from .torznab_api import TorznabAPI


# TODO: This is not a "Jackett" specific plugin, but a generic Torznab plugin. 
#       The user can create as many Torznab indexers as they want, pointing to Jackett, Prowlarr, or any other Torznab-compatible service.


class TorznabPlugin(BasePlugin):
    """Torznab indexer plugin.
    
    This plugin provides access to Torznab-compatible indexers.
    It can create multiple indexer instances with different configurations.
    """
    
    # Built-in book/literature categories, used when the user hasn't set their own
    # in the plugin settings and an indexer doesn't specify categories itself.
    DEFAULT_BOOK_CATEGORIES = [
        "7000",  # Books
        "7010",  # Books/Mags
        "7020",  # Books/EBook
        "7040",  # Books/Technical
        "7050",  # Books/Other
        "7060",  # Books/Foreign
        "100036",  # Other/E-Books
        "100920",  # Literature
        "111160",  # Literature - Non-English-translated
        "156719",  # Literature - English-translated
    ]
    
    name = "Torznab"
    version = "0.1.0"
    description = "Indexer plugin that integrates with Torznab-compatible services."
    enabled = True
    
    def start(self) -> None:
        print("Torznab plugin started")
    
    def stop(self) -> None:
        print("Torznab plugin stopped")
    
    def get_settings_schema(self) -> Dict[str, Any]:
        return {
            "book_categories": {
                "type": "string",
                "label": "Default book categories",
                "description": (
                    "Comma-separated Torznab category IDs to search when an indexer "
                    "does not specify its own."
                ),
                "default": ",".join(self.DEFAULT_BOOK_CATEGORIES),
            },
        }

    def default_categories(self) -> List[str]:
        """Categories from plugin settings, falling back to the built-in list."""
        raw = (self.config or {}).get("book_categories")
        if not raw:
            return list(self.DEFAULT_BOOK_CATEGORIES)
        return [part.strip() for part in raw.split(",") if part.strip()]

    def get_available_indexers(self) -> List[Dict[str, Any]]:
        """Return available indexers this plugin can provide.
        
        Returns:
            List containing one indexer config for Torznab
        """
        return [{
            "id": "torznab",
            "name": "Torznab",
            "description": "Torznab-compatible indexer (Jackett, Prowlarr, etc.)",
            "user_configurable": True,  # This indexer requires user configuration, not auto-created
            "config_schema": {
                "url": {"type": "string", "required": True, "description": "Base URL of the Torznab API"},
                "api_key": {"type": "string", "required": True, "description": "API key for authentication"}
            }
        }]
    
    def create_indexer(self, config: Dict[str, Any]) -> IndexerPlugin:
        """Create a configured Torznab indexer instance.
        
        Args:
            config: Configuration dictionary with 'url' and 'api_key'
            
        Returns:
            Configured TorznabIndexer instance
        """
        config = dict(config)
        config.setdefault("categories", self.default_categories())
        return TorznabIndexer(**config)



# TODO: Unclear how user created indexer instances are to inherit from IndexerPlugin.
#       Configs for user created indexers are saved in the database.
#       Each instance is used independently via the database configuration.
class TorznabIndexer(IndexerPlugin):
    """Torznab indexer implementation."""
    
    name = "Torznab"
    version = "0.1.0"
    description = "Torznab-compatible indexer"
    enabled = True
    
    def __init__(self, url: str, api_key: str | None = None, categories: List[str] | None = None, **kwargs: Any):
        super().__init__(**kwargs)
        self.url = url
        self.api_key = api_key
        self.categories = categories or TorznabPlugin.DEFAULT_BOOK_CATEGORIES
        self.api_client: TorznabAPI | None = None
    
    def start(self) -> None:
        """Initialize the indexer and create API client."""
        self.api_client = TorznabAPI(self.url, self.api_key)
    
    def stop(self) -> None:
        """Clean up the indexer and close API client."""
        if self.api_client:
            # Note: close() is async, but stop() is sync
            # In practice, httpx will clean up on garbage collection
            self.api_client = None
    
    async def connect(self) -> bool:
        """Test connection to the Torznab indexer.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            if not self.api_client:
                self.start()
            
            # Type assertion: api_client is guaranteed to be non-None after start()
            assert self.api_client is not None
            
            # Test connection by getting capabilities
            caps = await self.api_client.get_capabilities()
            return caps is not None and len(caps) > 0
        except Exception as e:
            print(f"Torznab connection test failed: {e}")
            return False
    
    async def search(self, query: str) -> list[dict]:
        """Search for content using Torznab.
        
        Args:
            query: Search query string
            
        Returns:
            List of search results
        """
        try:
            print(f"[DEBUG TorznabIndexer] Starting search for query: {query}")
            print(f"[DEBUG TorznabIndexer] URL: {self.url}")
            print(f"[DEBUG TorznabIndexer] Categories: {self.categories}")
            
            if not self.api_client:
                print(f"[DEBUG TorznabIndexer] API client not initialized, calling start()")
                self.start()
            
            # Type assertion: api_client is guaranteed to be non-None after start()
            assert self.api_client is not None
            
            print(f"[DEBUG TorznabIndexer] Calling api_client.search()")
            results = await self.api_client.search(
                query=query,
                categories=self.categories,
                limit=100
            )
            
            print(f"[DEBUG TorznabIndexer] Search returned {len(results)} results")
            return results
        except Exception as e:
            print(f"[ERROR TorznabIndexer] Torznab search failed: {e}")
            import traceback
            traceback.print_exc()
            return []
        
    async def get_feed(self) -> list[dict]:
        """Get the latest feed items from Torznab.
        
        Returns:
            List of recent feed items
        """
        try:
            if not self.api_client:
                self.start()
            
            # Type assertion: api_client is guaranteed to be non-None after start()
            assert self.api_client is not None
            
            results = await self.api_client.get_rss_feed(
                categories=self.categories,
                limit=100
            )
            
            return results
        except Exception as e:
            print(f"Torznab feed fetch failed: {e}")
            return []
