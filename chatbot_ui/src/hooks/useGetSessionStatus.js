import { useQuery } from "@tanstack/react-query";
import { API_BASE_URL } from "@/config";
import { CustomHttpError } from "@/lib/errors";

export const useGetSessionStatus = (botGuid, sessionGuid, userGuid) => {
  return useQuery({
    queryKey: ["bot", botGuid, "session", "status", sessionGuid, "user", userGuid],
    queryFn: async () => {
      const url = new URL(`/session/status/${sessionGuid}`, API_BASE_URL)
      url.searchParams.append("user_guid", userGuid)
      const response = await fetch(url)
      if (!response.ok) {
        const errorResponse = await response.json();
        throw new CustomHttpError("Failed to get session status.", response.status, errorResponse);
      }

      return response.json();
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
    enabled: !!(botGuid && sessionGuid && userGuid)
  });
}