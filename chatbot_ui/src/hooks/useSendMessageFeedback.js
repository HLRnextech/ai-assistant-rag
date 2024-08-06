import { useMutation, useQueryClient } from "@tanstack/react-query";
import { API_BASE_URL } from "@/config";
import { useChatbotState } from "@/state/chatbot-state";
import { CustomHttpError } from "@/lib/errors";
import { captureException } from "@/lib/utils";

export const useSendMessageFeedback = () => {
  const setMessageFeedback = useChatbotState(state => state.setMessageFeedback)
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ botGuid: _, sessionGuid, messageGuid, userGuid, feedback }) => {
      const url = new URL(`/session/feedback/${sessionGuid}/message/${messageGuid}`, API_BASE_URL)
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
        throw new CustomHttpError("Failed to send message feedback.", response.status, errorResponse);
      }

      return response.json()
    },
    onSuccess: (_, { botGuid, userGuid, sessionGuid, messageGuid, feedback }) => {
      // update feedback in react-query cache and zustand store
      setMessageFeedback(messageGuid, feedback)
      queryClient.setQueryData(
        ["messages", "bot", botGuid, "session", sessionGuid, "user", userGuid],
        (data) => {
          const updatedMessages = data.messages.map((m) => {
            if (m.guid === messageGuid) {
              return { ...m, feedback }
            }
            return m
          })
          return { ...data, messages: updatedMessages }
        }
      )
    },
    onError: (error, variables) => {
      captureException(error, variables)
    }
  })
}