import { useMutation, useQueryClient } from "@tanstack/react-query";
import { API_BASE_URL } from "@/config";
import { CustomHttpError } from "@/lib/errors";
import { captureException } from "@/lib/utils";

export const useSendSessionFeedback = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ botGuid: _, sessionGuid, userGuid, feedback }) => {
      const url = new URL(`/session/feedback/${sessionGuid}`, API_BASE_URL)
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_guid: userGuid,
          feedback
        })
      })

      if (!response.ok) {
        const errorResponse = await response.json();
        throw new CustomHttpError("Failed to send session feedback.", response.status, errorResponse);
      }

      return response.json()
    },
    onSuccess: (_, { botGuid, userGuid, sessionGuid, feedback }) => {
      // update feedback in react-query cache
      queryClient.setQueryData(
        ["bot", botGuid, "session", "status", sessionGuid, "user", userGuid],
        (data) => {
          return { ...data, feedback }
        }
      )
    },
    onError: (error, variables) => {
      captureException(error, variables)
    },
  })
}