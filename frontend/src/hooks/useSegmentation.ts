import { useQuery, useMutation } from "@tanstack/react-query";
import {
  fetchHealth,
  postSegmentation,
  SegmentRequest,
} from "@/lib/segmentApi";

export function useBackendHealth() {
  return useQuery({
    queryKey: ["backend-health"],
    queryFn: fetchHealth,
    retry: false,
    refetchInterval: 30_000,
  });
}

export function useSegmentation() {
  return useMutation({
    mutationFn: (params: SegmentRequest) => postSegmentation(params),
  });
}
