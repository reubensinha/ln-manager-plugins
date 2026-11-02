import axios from "axios";

/** Plugin routes live outside the versioned core API. */
const api = axios.create({ baseURL: "/api/plugins/Reviews" });

export interface ReviewMatch {
  external_id: number;
  title: string | null;
  site_url: string | null;
  confidence: "exact" | "likely" | "loose" | "manual";
  average_score?: number | null;
}

export interface Review {
  id: number;
  summary: string | null;
  score: number | null;
  rating: number | null;
  rating_amount: number | null;
  created_at: number | null;
  site_url: string | null;
  user: string | null;
  avatar: string | null;
}

export interface SeriesReviews {
  match: ReviewMatch | null;
  reviews: Review[];
}

export interface MatchCandidate {
  external_id: number;
  title: string | null;
  english_title: string | null;
  year: number | null;
  average_score: number | null;
  site_url: string | null;
  cover_image: string | null;
}

export async function getSeriesReviews(seriesId: string): Promise<SeriesReviews> {
  const response = await api.get(`/series/${seriesId}/reviews`);
  return response.data;
}

export async function getMatchCandidates(
  seriesId: string
): Promise<MatchCandidate[]> {
  const response = await api.get(`/series/${seriesId}/candidates`);
  return response.data;
}

export async function setSeriesMatch(
  seriesId: string,
  externalId: number
): Promise<ReviewMatch> {
  const response = await api.put(`/series/${seriesId}/match`, {
    external_id: externalId,
  });
  return response.data;
}

export const reviewsQueryKeys = {
  reviews: (seriesId: string) => ["plugin", "Reviews", "reviews", seriesId] as const,
  candidates: (seriesId: string) =>
    ["plugin", "Reviews", "candidates", seriesId] as const,
};
