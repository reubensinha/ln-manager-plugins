import {
  Anchor,
  Badge,
  Button,
  Group,
  Image,
  Modal,
  Stack,
  Text,
} from "@mantine/core";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getMatchCandidates,
  reviewsQueryKeys,
  setSeriesMatch,
} from "../api";

interface MatchPickerModalProps {
  seriesId: string;
  opened: boolean;
  onClose: () => void;
}

/** Lets the user correct which AniList entry a series is tied to. */
function MatchPickerModal({ seriesId, opened, onClose }: MatchPickerModalProps) {
  const queryClient = useQueryClient();
  const { data: candidates, isPending } = useQuery({
    queryKey: reviewsQueryKeys.candidates(seriesId),
    queryFn: () => getMatchCandidates(seriesId),
    enabled: opened,
  });

  const choose = useMutation({
    mutationFn: (externalId: number) => setSeriesMatch(seriesId, externalId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: reviewsQueryKeys.reviews(seriesId),
      });
      onClose();
    },
  });

  return (
    <Modal opened={opened} onClose={onClose} title="Choose the matching series" size="lg" centered>
      <Stack>
        {isPending && <Text>Searching AniList...</Text>}
        {!isPending && !candidates?.length && (
          <Text c="dimmed">AniList returned no light novels for this title.</Text>
        )}
        {candidates?.map((candidate) => (
          <Group key={candidate.external_id} justify="space-between" wrap="nowrap">
            <Group wrap="nowrap">
              {candidate.cover_image && (
                <Image src={candidate.cover_image} w={40} h={56} radius="sm" />
              )}
              <div>
                <Text size="sm">{candidate.title}</Text>
                {candidate.english_title && (
                  <Text size="xs" c="dimmed">
                    {candidate.english_title}
                  </Text>
                )}
                <Group gap="xs" mt={2}>
                  {candidate.year && <Badge size="xs" variant="light">{candidate.year}</Badge>}
                  {candidate.average_score != null && (
                    <Badge size="xs" variant="light" color="teal">
                      {candidate.average_score}%
                    </Badge>
                  )}
                  {candidate.site_url && (
                    <Anchor size="xs" href={candidate.site_url} target="_blank">
                      AniList
                    </Anchor>
                  )}
                </Group>
              </div>
            </Group>
            <Button
              size="xs"
              variant="light"
              loading={choose.isPending && choose.variables === candidate.external_id}
              onClick={() => choose.mutate(candidate.external_id)}
            >
              Use this
            </Button>
          </Group>
        ))}
      </Stack>
    </Modal>
  );
}

export default MatchPickerModal;
