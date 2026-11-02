import type { PluginManifest } from "../../types/Plugin";
import { QBittorrentClientConfig } from "./components/QBittorrentClientConfig";

const qBittorrentManifest: PluginManifest = {
  name: "qBittorrent",
  routes: [],
  navLinks: [],
  downloadClientConfigComponents: {
    qbittorrent: QBittorrentClientConfig,
  },
};

export default qBittorrentManifest;
