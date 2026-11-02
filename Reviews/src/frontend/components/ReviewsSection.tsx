import { useState } from "react";
import {
  Anchor,
  Avatar,
  Badge,
  Button,
  Card,
  Divider,
  Group,
  SimpleGrid,
  Skeleton,
  Text,
  Title,
} from "@mantine/core";
import { useQuery } from "@tanstack/react-query";

import type { SeriesSectionContext } from "../../../extensions/extensionPoints";
import { getSeriesReviews, reviewsQueryKeys, type Review } from "../api";
import MatchPickerModal from "./MatchPickerModal";

function ReviewCard({ review }: { review: Review }) {
  return (
    <Card withBorder padding="sm" radius="md">
      <Group justify="space-between" wrap="nowrap" mb="xs">
        <Group gap="xs" wrap="nowrap">
          <Avatar src={review.avatar} size="sm" radius="xl" />
          <Text size="sm" fw={500}>
            {review.user ?? "Unknown"}
          </Text>
        </Group>
        {review.score != null && (
          <Badge variant="light" color={review.score >= 70 ? "teal" : "orange"}>
            {review.score}
          </Badge>
        )}
      </Group>

      <Text size="sm" lineClamp={4}>
        {review.summary}
      </Text>

      {review.site_url && (
        <Anchor size="xs" href={review.site_url} target="_blank" mt="xs">
          Read on AniList
        </Anchor>
      )}
    </Card>
  );
}

/** Community reviews for the series currently on screen. */
function ReviewsSection({ context }: { context: SeriesSectionContext }) {
  const seriesId = context.series.id;
  const [pickerOpen, setPickerOpen] = useState(false);

  const { data, isPending, isError } = useQuery({
    queryKey: reviewsQueryKeys.reviews(seriesId),
    queryFn: () => getSeriesReviews(seriesId),
  });

  if (isError) return null;

  return (
    <>
      <Divider my="xl" />
      <Group justify="space-between" mb="md">
        <Group gap="sm">
          <Title order={4}>Reviews</Title>
          {data?.match?.average_score != null && (
            <Badge variant="light" color="teal">
              {data.match.average_score}% on AniList
            </Badge>
          )}
          {data?.match?.confidence === "loose" && (
            <Badge variant="light" color="yellow">
              uncertain match
            </Badge>
          )}
        </Group>

        <Group gap="xs">
          {data?.match?.site_url && (
            <Anchor size="sm" href={data.match.site_url} target="_blank">
              {data.match.title}
            </Anchor>
          )}
          <Button size="xs" variant="subtle" onClick={() => setPickerOpen(true)}>
            {data?.match ? "Wrong series?" : "Find series"}
          </Button>
        </Group>
      </Group>

      {isPending && <Skeleton height={120} />}

      {!isPending && !data?.match && (
        <Text c="dimmed" size="sm">
          No matching series found on AniList.
        </Text>
      )}

      {!isPending && data?.match && data.reviews.length === 0 && (
        <Text c="dimmed" size="sm">
          No one has reviewed this series on AniList yet.
        </Text>
      )}

      {!!data?.reviews.length && (
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
          {data.reviews.map((review) => (
            <ReviewCard key={review.id} review={review} />
          ))}
        </SimpleGrid>
      )}

      <MatchPickerModal
        seriesId={seriesId}
        opened={pickerOpen}
        onClose={() => setPickerOpen(false)}
      />
    </>
  );
}

export default ReviewsSection;
