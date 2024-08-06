import { useMutation } from "@tanstack/react-query";
import { API_BASE_URL } from "@/config";
import { CustomHttpError } from "@/lib/errors";
import { useChatbotState } from "@/state/chatbot-state";
import { captureException } from "@/lib/utils";

export const useTriggerBotMessage = () => {
  const appendMessage = useChatbotState((state) => state.appendMessage)

  return useMutation({
    mutationFn: async ({ userGuid, messageType, sessionGuid }) => {
      const url = new URL(`/session/trigger_bot_message/${sessionGuid}`, API_BASE_URL)
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_guid: userGuid,
          message_type: messageType
        })
      })

      if (!response.ok) {
        const errorResponse = await response.json();
        throw new CustomHttpError("Failed to trigger bot message.", response.status, errorResponse);
      }

      return response.json()
    },
    onSuccess: (data) => {
      appendMessage(data)
    },
    onError: (error, variables) => {
      captureException(error, variables)
    }
  })
}