import { useMutation } from "@tanstack/react-query";
import { API_BASE_URL } from "@/config";
import { useChatbotState } from "@/state/chatbot-state";
import { CustomHttpError } from "@/lib/errors";
import { captureException } from "@/lib/utils";

export const useCreateSession = () => {
  const setSessionGuid = useChatbotState(state => state.setSessionGuid)

  return useMutation({
    mutationFn: async ({ botGuid, userGuid }) => {
      const url = new URL(`/session/create`, API_BASE_URL)
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_guid: userGuid,
          bot_guid: botGuid,
        })
      })

      if (!response.ok) {
        const errorResponse = await response.json();
        throw new CustomHttpError("Failed to create session.", response.status, errorResponse);
      }

      return response.json()
    },
    onSuccess: (data) => {
      setSessionGuid(data.guid)
    },
    onError: (error, variables) => {
      captureException(error, variables)
    }
  })
}