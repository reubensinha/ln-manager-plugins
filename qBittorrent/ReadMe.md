# qBittorrent Download Client Plugin

This plugin provides integration with qBittorrent download client through the qBittorrent Web API v2.

## Features

- Add torrents via magnet links, torrent URLs, or torrent files
- Retrieve torrent metadata and status
- List all active downloads
- Test connection to qBittorrent server
- Full support for authentication and SSL connections

## Configuration

The plugin requires the following configuration parameters:

| Parameter  | Type    | Required | Default | Description                                       |
|-----------|---------|----------|---------|---------------------------------------------------|
| host      | string  | Yes      | -       | Hostname or IP address of the qBittorrent server |
| port      | integer | Yes      | -       | Port number of the qBittorrent server            |
| username  | string  | Yes      | -       | Username for qBittorrent authentication          |
| password  | string  | Yes      | -       | Password for qBittorrent authentication          |
| use_ssl   | boolean | No       | false   | Whether to use HTTPS for the connection          |

## Example Configuration

```json
{
  "host": "localhost",
  "port": 8080,
  "username": "admin",
  "password": "adminpass",
  "use_ssl": false
}
```

## API Methods

### `download(info_hash, magnet_link, torrent_file)`
Add a torrent to qBittorrent. At least one parameter must be provided.

- **info_hash**: Hash of the torrent (will be converted to magnet link)
- **magnet_link**: Magnet link to download
- **torrent_file**: Path to .torrent file

Returns `True` if successful, `False` otherwise.

### `get_metadata(info_hash)`
Retrieve detailed metadata for a specific torrent.

Returns a dictionary containing:
- Basic info (name, size, status, progress)
- Transfer info (download/upload speeds, ETA, ratio)
- Peer info (seeds, peers)
- File list
- Timestamps (added_on, completion_on)

### `test_connection()`
Test the connection to the qBittorrent server.

Returns a dictionary with:
- `success`: Boolean indicating connection status
- `version`: qBittorrent version (if successful)
- `api_version`: Web API version (if successful)
- `message`: Status message

### `get_all_downloads()`
Retrieve a list of all torrents in qBittorrent.

Returns a list of dictionaries, each containing:
- `info_hash`: Torrent hash
- `name`: Torrent name
- `size`: Total size in bytes
- `progress`: Download progress (0-100)
- `status`: Current state
- `download_speed`: Download speed in bytes/sec
- `upload_speed`: Upload speed in bytes/sec
- `eta`: Estimated time remaining
- `seeds`: Number of seeders
- `peers`: Number of peers
- `ratio`: Share ratio
- `category`: Assigned category
- `tags`: Assigned tags

## Requirements

- qBittorrent v4.1 or higher
- Web UI enabled in qBittorrent settings
- Valid authentication credentials

## Setup

1. Enable the Web UI in qBittorrent:
   - Open qBittorrent
   - Go to Tools > Options > Web UI
   - Check "Enable the Web User Interface"
   - Set a port (default: 8080)
   - Configure authentication

2. The plugin will be automatically loaded from the `backend/plugins/qBittorrent/` directory

## Notes

- The plugin uses the qBittorrent Web API v2
- All API calls are asynchronous
- The plugin maintains a single HTTP client session for efficiency
- Authentication is handled automatically on first API call
