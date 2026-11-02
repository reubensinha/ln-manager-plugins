"""Torznab API client implementation following the Torznab specification."""

import httpx
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional
from datetime import datetime


class TorznabAPI:
    """Client for interacting with Torznab-compatible indexers."""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        """Initialize the Torznab API client.
        
        Args:
            base_url: Base URL of the Torznab API endpoint
            api_key: Optional API key for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    def _build_params(self, params: Dict[str, Any]) -> Dict[str, str]:
        """Build query parameters including API key if present.
        
        Args:
            params: Dictionary of parameters
            
        Returns:
            Complete parameter dictionary with API key if configured
        """
        result = {k: str(v) for k, v in params.items()}
        if self.api_key:
            result['apikey'] = self.api_key
        return result
    
    async def get_capabilities(self) -> Dict[str, Any]:
        """Get the capabilities of the Torznab indexer.
        
        Returns:
            Dictionary containing indexer capabilities
        """
        params = self._build_params({'t': 'caps'})
        
        response = await self.client.get(self.base_url, params=params)
        response.raise_for_status()
        
        root = ET.fromstring(response.text)
        
        # Parse capabilities
        caps = {
            'searching': {},
            'categories': []
        }
        
        # Parse search capabilities
        searching = root.find('.//searching')
        if searching is not None:
            for search_type in searching:
                caps['searching'][search_type.tag] = {
                    'available': search_type.get('available', 'no') == 'yes',
                    'supportedParams': search_type.get('supportedParams', '').split(',') if search_type.get('supportedParams') else []
                }
        
        # Parse categories
        categories = root.find('.//categories')
        if categories is not None:
            for category in categories.findall('category'):
                cat_info = {
                    'id': category.get('id'),
                    'name': category.get('name'),
                    'subcategories': []
                }
                for subcat in category.findall('subcat'):
                    cat_info['subcategories'].append({
                        'id': subcat.get('id'),
                        'name': subcat.get('name')
                    })
                caps['categories'].append(cat_info)
        
        return caps
    
    async def search(
        self, 
        query: str, 
        categories: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Search the indexer for content.
        
        Args:
            query: Search query string
            categories: Optional list of category IDs to search within
            limit: Maximum number of results to return
            offset: Offset for pagination
            
        Returns:
            List of search results
        """
        params = {
            't': 'search',
            'q': query,
            'limit': limit,
            'offset': offset
        }
        
        if categories:
            params['cat'] = ','.join(categories)
        
        params = self._build_params(params)
        
        response = await self.client.get(self.base_url, params=params)
        response.raise_for_status()
        
        return self._parse_rss_feed(response.text)
    
    async def get_rss_feed(
        self,
        categories: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get the latest items from the RSS feed.
        
        Args:
            categories: Optional list of category IDs to filter by
            limit: Maximum number of results to return
            
        Returns:
            List of feed items
        """
        # For RSS feed, we can use search with empty query
        # or use a different endpoint if the indexer supports it
        params = {
            't': 'search',
            'limit': limit
        }
        
        if categories:
            params['cat'] = ','.join(categories)
        
        params = self._build_params(params)
        
        response = await self.client.get(self.base_url, params=params)
        response.raise_for_status()
        
        return self._parse_rss_feed(response.text)
    
    def _parse_rss_feed(self, xml_content: str) -> List[Dict[str, Any]]:
        """Parse RSS feed XML into a list of items.
        
        Args:
            xml_content: RSS feed XML content
            
        Returns:
            List of parsed feed items
        """
        root = ET.fromstring(xml_content)
        
        # Handle both RSS and Atom feeds
        items = []
        
        # Try RSS format first
        for item in root.findall('.//item'):
            parsed_item = self._parse_rss_item(item)
            if parsed_item:
                items.append(parsed_item)
        
        return items
    
    def _parse_rss_item(self, item: ET.Element) -> Optional[Dict[str, Any]]:
        """Parse a single RSS item.
        
        Args:
            item: XML element representing an RSS item
            
        Returns:
            Parsed item dictionary or None if parsing fails
        """
        try:
            # Namespace for Torznab attributes
            torznab_ns = {'torznab': 'http://torznab.com/schemas/2015/feed'}
            
            result = {
                'title': self._get_element_text(item, 'title'),
                'link': self._get_element_text(item, 'link'),
                'description': self._get_element_text(item, 'description'),
                'guid': self._get_element_text(item, 'guid'),
                'pub_date': self._get_element_text(item, 'pubDate'),
                'size': None,
                'category': [],
                'torznab_attrs': {}
            }
            
            # Parse enclosure for download link and size
            enclosure = item.find('enclosure')
            if enclosure is not None:
                result['download_url'] = enclosure.get('url')
                result['size'] = int(enclosure.get('length', 0))
            
            # Parse categories
            for cat in item.findall('category'):
                if cat.text:
                    result['category'].append(cat.text)
            
            # Parse Torznab attributes
            for attr in item.findall('torznab:attr', torznab_ns):
                name = attr.get('name')
                value = attr.get('value')
                if name and value:
                    result['torznab_attrs'][name] = value
            
            # Extract common Torznab attributes to top level
            if 'size' in result['torznab_attrs']:
                result['size'] = int(result['torznab_attrs']['size'])
            if 'seeders' in result['torznab_attrs']:
                result['seeders'] = int(result['torznab_attrs']['seeders'])
            if 'peers' in result['torznab_attrs']:
                result['peers'] = int(result['torznab_attrs']['peers'])
            if 'grabs' in result['torznab_attrs']:
                result['grabs'] = int(result['torznab_attrs']['grabs'])
            
            return result
        except Exception as e:
            print(f"Error parsing RSS item: {e}")
            return None
    
    def _get_element_text(self, parent: ET.Element, tag: str) -> Optional[str]:
        """Safely get text content from an XML element.
        
        Args:
            parent: Parent XML element
            tag: Tag name to find
            
        Returns:
            Text content or None if not found
        """
        element = parent.find(tag)
        return element.text if element is not None else None
