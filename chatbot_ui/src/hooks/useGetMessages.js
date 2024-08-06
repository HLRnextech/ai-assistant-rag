import { useQuery } from "@tanstack/react-query";
import { API_BASE_URL } from "@/config";
import { CustomHttpError } from "@/lib/errors";

export const useGetMessages = (botGuid, sessionGuid, userGuid) => {
  return useQuery({
    // querykey of messages needs to have a separate root because we render msgs from zustand and react-query
    // and a refetch from server might introduce duplicate messages
    queryKey: ["messages", "bot", botGuid, "session", sessionGuid, "user", userGuid],
    queryFn: async () => {
      const url = new URL(`/session/list_messages/${sessionGuid}`, API_BASE_URL)
      url.searchParams.append("user_guid", userGuid)

      const response = await fetch(url)
      if (!response.ok) {
        const errorResponse = await response.json();
        throw new CustomHttpError("Failed to get messages.", response.status, errorResponse);
      }

      return response.json();
    },
    staleTime: Infinity,
    enabled: !!(botGuid && sessionGuid && userGuid),
  });
}