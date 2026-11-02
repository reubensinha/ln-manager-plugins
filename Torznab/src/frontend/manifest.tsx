import type { PluginManifest } from "../../types/Plugin";
import { TorznabIndexerConfig } from "./components/TorznabIndexerConfig";

const TorznabManifest: PluginManifest = {
  name: "Torznab",
  routes: [],
  navLinks: [],
  indexerConfigComponents: {
    // The key should match the capability.id from the backend
    "torznab": TorznabIndexerConfig,
  },
};

export default TorznabManifest;
