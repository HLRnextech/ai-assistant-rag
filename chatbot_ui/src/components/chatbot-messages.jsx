import React, { useLayoutEffect } from "react";
import { AlertCircle } from "lucide-react"
import { BeatLoader } from "react-spinners";

import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert.jsx";
import BotMessage from "@/components/bot-message.jsx";
import UserMessage from "@/components/user-message.jsx";

import { useChatbotState } from "@/state/chatbot-state.js";
import { useGetMessages } from "@/hooks/useGetMessages.js";
import { INITIAL_SCROLL_DELAY_MS } from "@/config.js";


const ChatbotMessages = ({ isMsgStreaming, isFirstTokenReceived, scrollToBottom }) => {
  const userGuid = useChatbotState(state => state.userGuid)
  const sessionGuid = useChatbotState(state => state.sessionGuid)
  const botGuid = useChatbotState(state => state.botGuid)
  const messages = useChatbotState(state => state.messages)

  const {
    data,
    isLoading,
    isPending,
    isError
  } = useGetMessages(botGuid, sessionGuid, userGuid)

  const initialMessages = data?.messages;

  useLayoutEffect(() => {
    if (initialMessages?.length > 0) {
      setTimeout(() => scrollToBottom(true), INITIAL_SCROLL_DELAY_MS)
    }
  }, [initialMessages])

  if (isError) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Heads up!</AlertTitle>
        <AlertDescription>
          We were unable to fetch the messages. Please try again later.
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <>
      <BeatLoader loading={isLoading || isPending} speedMultiplier={0.3} size={6} />
      {
        initialMessages?.map(m => (
          m.role === "bot" ?
            <BotMessage key={m.guid} message={m} />
            :
            <UserMessage key={m.guid} message={m} />
        ))
      }
      {messages.map((m) => (
        m.role === "bot" ?
          <BotMessage key={m.guid} message={m} />
          :
          <UserMessage key={m.guid} message={m} />
      ))}
      <BeatLoader loading={isMsgStreaming && !isFirstTokenReceived} speedMultiplier={0.3} size={6} />
    </>
  )
}

export default ChatbotMessages;
