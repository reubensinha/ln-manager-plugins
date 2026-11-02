from typing import Any, Dict, List
from backend.core.plugins.base import BasePlugin
from backend.core.plugins.download_client import DownloadClientPlugin
from backend.core.logging_config import get_plugin_logger
from .qbittorrent_api import QBittorrentAPI

logger = get_plugin_logger("qBittorrent")


class qBittorrentPlugin(BasePlugin):
    """qBittorrent download client plugin.

    This plugin provides access to qBittorrent download clients.
    """

    name = "qBittorrent"
    version = "0.1.0"
    description = "Download client plugin that integrates with qBittorrent."
    enabled = True

    def start(self) -> None:
        print("qBittorrent plugin started")

    def stop(self) -> None:
        print("qBittorrent plugin stopped")

    def get_available_clients(self) -> List[Dict[str, Any]]:
        """Return available download clients this plugin can provide.
        Returns:
            List containing one client config for qBittorrent
        """

        return [
            {
                "id": "qbittorrent",
                "name": "qBittorrent",
                "description": "qBittorrent download client",
                "user_configurable": True,
                "config_schema": {
                    "host": {
                        "type": "string",
                        "required": True,
                        "description": "Hostname or IP address of the qBittorrent server",
                    },
                    "port": {
                        "type": "integer",
                        "required": True,
                        "description": "Port number of the qBittorrent server",
                    },
                    "username": {
                        "type": "string",
                        "required": True,
                        "description": "Username for qBittorrent authentication",
                    },
                    "password": {
                        "type": "string",
                        "required": True,
                        "description": "Password for qBittorrent authentication",
                    },
                    "use_ssl": {
                        "type": "boolean",
                        "required": False,
                        "default": False,
                        "description": "Whether to use SSL for the connection",
                    },
                },
            }
        ]

    def create_download_client(self, config: Dict[str, Any]):
        """Create an instance of the qBittorrent download client with the given configuration.

        Args:
            config: Configuration dictionary for the qBittorrent client

        Returns:
            Instance of qBittorrentClient
        """
        return qBittorrentClient(config)


class qBittorrentClient(DownloadClientPlugin):
    """qBittorrent download client implementation."""

    name = "qBittorrent"
    version = "0.1.0"
    description = "qBittorrent download client"
    enabled = True

    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.host: str = config.get("host", "")
        self.port: int = config.get("port", 8080)
        self.username: str = config.get("username", "")
        self.password: str = config.get("password", "")
        self.use_ssl: bool = config.get("use_ssl", False)
        self.api_client: QBittorrentAPI | None = None
        self._initialized = False

    def _ensure_api_client(self) -> None:
        """Ensure the API client is initialized."""
        if self.api_client is None:
            if not self.host or not self.username:
                raise ValueError(
                    "Host and username are required for qBittorrent client"
                )

            self.api_client = QBittorrentAPI(
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                use_ssl=self.use_ssl,
            )
            self._initialized = True

    def start(self) -> None:
        """Initialize the qBittorrent client."""
        logger.info(f"Starting qBittorrent client for {self.host}:{self.port}")
        self._ensure_api_client()

    def stop(self) -> None:
        """Stop the qBittorrent client."""
        logger.info("Stopping qBittorrent client")
        if self.api_client:
            # Clean up if needed
            pass

    async def download(
        self,
        info_hash: str | None = None,
        magnet_link: str | None = None,
        torrent_file: str | None = None,
    ) -> bool:
        """Download content using qBittorrent.

        Args:
            info_hash: Info hash of the torrent to download (not directly supported)
            magnet_link: Magnet link of the torrent to download
            torrent_file: Path to the torrent file to download

        Returns:
            True if the download was successfully added, False otherwise
        """
        self._ensure_api_client()
        assert self.api_client is not None

        try:
            # Try magnet link first (most reliable)
            if magnet_link:
                logger.info(f"Adding magnet link to qBittorrent")
                result = await self.api_client.add_torrent_url(magnet_link)
                if result:
                    logger.info("Successfully added magnet link")
                    return True
                else:
                    logger.warning("Failed to add magnet link, will try other methods if available")

            # Try torrent file if magnet failed or wasn't available
            if torrent_file:
                logger.info(f"Adding torrent file to qBittorrent: {torrent_file}")
                result = await self.api_client.add_torrent_file(torrent_file)
                if result:
                    logger.info("Successfully added torrent file")
                    return True
                else:
                    logger.warning("Failed to add torrent file")

            # Try info_hash as last resort
            if info_hash:
                # Convert info_hash to magnet link
                magnet = f"magnet:?xt=urn:btih:{info_hash}"
                logger.info(
                    f"Converting info_hash to magnet link and adding to qBittorrent"
                )
                result = await self.api_client.add_torrent_url(magnet)
                if result:
                    logger.info("Successfully added torrent via info_hash")
                    return True

            # If we get here, either nothing was provided or all methods failed
            if not magnet_link and not torrent_file and not info_hash:
                logger.error("No download information provided")
                raise ValueError(
                    "At least one of info_hash, magnet_link, or torrent_file must be provided"
                )
            
            logger.error("All download methods failed")
            return False

        except Exception as e:
            logger.error(f"Failed to add download to qBittorrent: {str(e)}")
            return False

    async def test_connection(self) -> dict:
        """Test connection to the qBittorrent server.

        Returns:
            Dictionary with connection status and server information
        """
        self._ensure_api_client()
        assert self.api_client is not None

        try:
            result = await self.api_client.test_connection()
            logger.info(f"Connection test result: {result}")
            return result
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return {"success": False, "message": f"Connection test failed: {str(e)}"}

    async def get_all_downloads(self) -> list[dict]:
        """Retrieve a list of all current downloads with status from the download client.

        Returns:
            List of dictionaries containing download information
        """
        self._ensure_api_client()
        assert self.api_client is not None

        try:
            # Get all torrents
            torrents = await self.api_client.get_torrent_list()

            # Transform to a standardized format
            downloads = []
            for torrent in torrents:
                download = {
                    "info_hash": torrent.get("hash"),
                    "name": torrent.get("name"),
                    "size": torrent.get("size"),
                    "progress": torrent.get("progress", 0)
                    * 100,  # Convert to percentage
                    "status": torrent.get("state"),
                    "download_speed": torrent.get("dlspeed", 0),
                    "upload_speed": torrent.get("upspeed", 0),
                    "eta": torrent.get("eta"),
                    "seeds": torrent.get("num_seeds", 0),
                    "peers": torrent.get("num_leechs", 0),
                    "ratio": torrent.get("ratio", 0),
                    "category": torrent.get("category"),
                    "tags": torrent.get("tags"),
                    "added_on": torrent.get("added_on"),
                }
                downloads.append(download)

            logger.info(f"Retrieved {len(downloads)} downloads from qBittorrent")
            return downloads

        except Exception as e:
            logger.error(f"Failed to get downloads from qBittorrent: {str(e)}")
            return []

    async def remove_download(self, info_hash: str, delete_data: bool = False) -> bool:
        """Remove a download from the download client.

        Args:
            info_hash: Info hash of the download to remove
            delete_data: Whether to delete the downloaded data as well

        Returns:
            True if the download was successfully removed, False otherwise
        """
        self._ensure_api_client()
        assert self.api_client is not None

        try:
            logger.info(f"Removing torrent {info_hash} (delete_data={delete_data})")
            result = await self.api_client.delete_torrents(
                hashes=[info_hash], delete_files=delete_data
            )
            
            if result:
                logger.info(f"Successfully removed torrent {info_hash}")
            else:
                logger.warning(f"Failed to remove torrent {info_hash}")
            
            return result
        except Exception as e:
            logger.error(f"Error removing torrent {info_hash}: {str(e)}")
            return False
