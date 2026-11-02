import type { PluginManifest } from "../../types/Plugin";
import { extensionPoints } from "../../extensions/extensionPoints";
import ReviewsSection from "./components/ReviewsSection";

const ReviewsManifest: PluginManifest = {
  name: "Reviews",
  routes: [],
  navLinks: [],
  extensions: [
    {
      point: extensionPoints.seriesDetailBottom,
      id: "series-reviews",
      component: ReviewsSection,
    },
  ],
};

export default ReviewsManifest;
