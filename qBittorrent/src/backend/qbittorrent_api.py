"""qBittorrent Web API client wrapper.

This module provides a thin wrapper around the qbittorrent-api package.
For full API documentation, see: https://qbittorrent-api.readthedocs.io/
"""

import asyncio

from qbittorrentapi import Client
from typing import Dict, List, Any, Optional


class QBittorrentAPI:
    """Wrapper for qbittorrent-api Client."""
    
    def __init__(
        self, 
        host: str, 
        port: int, 
        username: str, 
        password: str, 
        use_ssl: bool = False
    ):
        """Initialize the qBittorrent API client.
        
        Args:
            host: Hostname or IP address of the qBittorrent server
            port: Port number of the qBittorrent server
            username: Username for authentication
            password: Password for authentication
            use_ssl: Whether to use HTTPS
        """
        self.client = Client(
            host=host,
            port=port,
            username=username,
            password=password,
            VERIFY_WEBUI_CERTIFICATE=False  # Allow self-signed certs
        )
    
    async def close(self):
        """Close the client connection."""
        # The qbittorrent-api Client doesn't require explicit closing
        pass
    
    async def login(self) -> bool:
        """Authenticate with the qBittorrent server.
        
        Returns:
            True if login was successful
        """
        try:
            await asyncio.to_thread(self.client.auth_log_in)
            return True
        except Exception as e:
            raise Exception(f"Login failed: {str(e)}")
    
    async def logout(self) -> bool:
        """Logout from the qBittorrent server.
        
        Returns:
            True if logout was successful
        """
        try:
            await asyncio.to_thread(self.client.auth_log_out)
            return True
        except Exception:
            return False
    
    async def get_version(self) -> str:
        """Get qBittorrent version.
        
        Returns:
            Version string
        """
        return await asyncio.to_thread(lambda: self.client.app.version)
    
    async def get_api_version(self) -> str:
        """Get Web API version.
        
        Returns:
            API version string
        """
        return await asyncio.to_thread(lambda: self.client.app.web_api_version)
    
    async def add_torrent_url(
        self, 
        urls: str | List[str],
        savepath: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        paused: bool = False,
        **kwargs
    ) -> bool:
        """Add torrent(s) from URL(s) (magnet links or http URLs).
        
        Args:
            urls: Single URL or list of URLs (magnet links or http links to .torrent files)
            savepath: Path where the torrent content should be saved
            category: Category for the torrent
            tags: List of tags to apply
            paused: Whether to add torrent in paused state
            **kwargs: Additional parameters supported by qBittorrent API
            
        Returns:
            True if torrents were added successfully
        """
        try:
            await asyncio.to_thread(
                lambda: self.client.torrents_add(
                    urls=urls,
                    save_path=savepath,
                    category=category,
                    tags=tags,
                    is_paused=paused,
                    **kwargs
                )
            )
            return True
        except Exception:
            return False
    
    async def add_torrent_file(
        self,
        torrent_file: str | bytes,
        savepath: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        paused: bool = False,
        **kwargs
    ) -> bool:
        """Add torrent from file.
        
        Args:
            torrent_file: Path to torrent file or raw torrent file data
            savepath: Path where the torrent content should be saved
            category: Category for the torrent
            tags: List of tags to apply
            paused: Whether to add torrent in paused state
            **kwargs: Additional parameters supported by qBittorrent API
            
        Returns:
            True if torrent was added successfully
        """
        def _add() -> None:
            # Handle file path vs bytes
            if isinstance(torrent_file, str):
                with open(torrent_file, 'rb') as f:
                    file_data = f.read()
            else:
                file_data = torrent_file

            self.client.torrents_add(
                torrent_files=file_data,
                save_path=savepath,
                category=category,
                tags=tags,
                is_paused=paused,
                **kwargs
            )

        try:
            await asyncio.to_thread(_add)
            return True
        except Exception:
            return False
    
    async def get_torrent_list(
        self,
        filter: Optional[str] = None,
        category: Optional[str] = None,
        tag: Optional[str] = None,
        sort: Optional[str] = None,
        reverse: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        hashes: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get list of torrents.
        
        Args:
            filter: Filter torrent list (all, downloading, seeding, completed, paused, etc.)
            category: Filter by category
            tag: Filter by tag
            sort: Sort torrents by property
            reverse: Enable reverse sorting
            limit: Limit number of results
            offset: Offset for pagination
            hashes: Filter by torrent hashes
            
        Returns:
            List of torrent dictionaries
        """
        # Build kwargs to avoid type issues
        kwargs: Dict[str, Any] = {}
        if filter is not None:
            kwargs["status_filter"] = filter
        if category is not None:
            kwargs["category"] = category
        if tag is not None:
            kwargs["tag"] = tag
        if sort is not None:
            kwargs["sort"] = sort
        kwargs["reverse"] = reverse
        if limit is not None:
            kwargs["limit"] = limit
        if offset is not None:
            kwargs["offset"] = offset
        if hashes is not None:
            kwargs["torrent_hashes"] = hashes
        
        torrents = await asyncio.to_thread(lambda: self.client.torrents_info(**kwargs))  # type: ignore
        # Convert to list of dicts
        return [dict(t) for t in torrents]
    
    async def get_torrent_properties(self, torrent_hash: str) -> Dict[str, Any]:
        """Get properties of a specific torrent.
        
        Args:
            torrent_hash: Hash of the torrent
            
        Returns:
            Dictionary containing torrent properties
        """
        props = await asyncio.to_thread(
            lambda: self.client.torrents_properties(torrent_hash=torrent_hash)
        )
        return dict(props)
    
    async def get_torrent_trackers(self, torrent_hash: str) -> List[Dict[str, Any]]:
        """Get trackers of a specific torrent.
        
        Args:
            torrent_hash: Hash of the torrent
            
        Returns:
            List of tracker dictionaries
        """
        trackers = await asyncio.to_thread(
            lambda: self.client.torrents_trackers(torrent_hash=torrent_hash)
        )
        return [dict(t) for t in trackers]
    
    async def get_torrent_contents(self, torrent_hash: str) -> List[Dict[str, Any]]:
        """Get contents (files) of a specific torrent.
        
        Args:
            torrent_hash: Hash of the torrent
            
        Returns:
            List of file dictionaries
        """
        files = await asyncio.to_thread(
            lambda: self.client.torrents_files(torrent_hash=torrent_hash)
        )
        return [dict(f) for f in files]
    
    async def pause_torrents(self, hashes: List[str]) -> bool:
        """Pause one or more torrents.
        
        Args:
            hashes: List of torrent hashes (use ['all'] to pause all)
            
        Returns:
            True if successful
        """
        try:
            target = 'all' if hashes == ['all'] else hashes
            await asyncio.to_thread(
                lambda: self.client.torrents_pause(torrent_hashes=target)
            )
            return True
        except Exception:
            return False
    
    async def resume_torrents(self, hashes: List[str]) -> bool:
        """Resume one or more torrents.
        
        Args:
            hashes: List of torrent hashes (use ['all'] to resume all)
            
        Returns:
            True if successful
        """
        try:
            target = 'all' if hashes == ['all'] else hashes
            await asyncio.to_thread(
                lambda: self.client.torrents_resume(torrent_hashes=target)
            )
            return True
        except Exception:
            return False
    
    async def delete_torrents(
        self, 
        hashes: List[str], 
        delete_files: bool = False
    ) -> bool:
        """Delete one or more torrents.
        
        Args:
            hashes: List of torrent hashes
            delete_files: Whether to delete downloaded files as well
            
        Returns:
            True if successful
        """
        try:
            await asyncio.to_thread(
                lambda: self.client.torrents_delete(
                    delete_files=delete_files,
                    torrent_hashes=hashes
                )
            )
            return True
        except Exception:
            return False
    
    async def get_categories(self) -> Dict[str, Dict[str, Any]]:
        """Get all categories.
        
        Returns:
            Dictionary of categories
        """
        categories = await asyncio.to_thread(self.client.torrents_categories)
        # Convert to plain dict
        result: Dict[str, Dict[str, Any]] = {}
        for key, value in categories.items():
            result[key] = dict(value)  # type: ignore
        return result
    
    async def get_tags(self) -> List[str]:
        """Get all tags.
        
        Returns:
            List of tag names
        """
        tags = await asyncio.to_thread(self.client.torrents_tags)
        return [str(tag) for tag in tags]
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to qBittorrent server.
        
        Returns:
            Dictionary with connection status and server info
        """
        try:
            version = await self.get_version()
            api_version = await self.get_api_version()
            
            return {
                "success": True,
                "version": version,
                "api_version": api_version,
                "message": "Successfully connected to qBittorrent"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection failed: {str(e)}"
            }
