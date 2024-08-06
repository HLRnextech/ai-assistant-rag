import { useMutation } from "@tanstack/react-query";
import { API_BASE_URL } from "@/config";
import { CustomHttpError } from "@/lib/errors";
import { captureException } from "@/lib/utils";

export const useEndSession = () => {
  return useMutation({
    mutationFn: async ({ userGuid, sessionGuid, botGuid: _ }) => {
      const url = new URL(`/session/end/${sessionGuid}`, API_BASE_URL)
      const response = await fetch(url, {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_guid: userGuid,
        })
      })

      if (!response.ok) {
        const errorResponse = await response.json();
        throw new CustomHttpError("Failed to end session.", response.status, errorResponse);
      }

      return response.json()
    },
    onError: (error, variables) => {
      captureException(error, variables)
    }
  })
}