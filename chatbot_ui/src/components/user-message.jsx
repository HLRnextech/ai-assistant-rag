import React from "react";

import { useChatbotState } from "@/state/chatbot-state.js";
import { useGetBotData } from "@/hooks/useGetBotData.js";

const UserMessage = ({ message }) => {
  const botGuid = useChatbotState(state => state.botGuid)
  const { data: botData } = useGetBotData(botGuid);

  return (
    <div className="w-full">
      <div
        className="flex justify-start bg-[var(--bgcolor)] text-chatUserMessageText rounded-xl rounded-br-none w-fit max-w-[80%] h-full ml-auto p-4"
        style={{
          '--bgcolor': botData?.configuration?.secondary_color || DEFAULT_SECONDARY_COLOR
        }}
      >
        {message.content}
      </div>
    </div>
  )
};

export default UserMessage;