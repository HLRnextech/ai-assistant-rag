import { useQuery } from "@tanstack/react-query";
import { API_BASE_URL } from "@/config";
import { CustomHttpError } from "@/lib/errors";

export const useGetBotData = (botGuid) => {
  return useQuery({
    queryKey: ["bot", botGuid],
    queryFn: async () => {
      const url = new URL(`/bot/details/${botGuid}`, API_BASE_URL)
      const response = await fetch(url)
      if (!response.ok) {
        const errorResponse = await response.json();
        throw new CustomHttpError("Failed to load bot data.", response.status, errorResponse);
      }

      return response.json();
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
    enabled: !!botGuid,
  });
}