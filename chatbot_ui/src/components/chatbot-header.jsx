import React from "react";
import { PopoverClose } from "@radix-ui/react-popover";

import { CardHeader, CardTitle } from "@/components/ui/card.jsx";
import { Button } from "@/components/ui/button.jsx";
import BotAvatar from "./bot-avatar.jsx";

import CloseIcon from "@/assets/close.svg";
import { useGetBotData } from "@/hooks/useGetBotData.js";
import { useChatbotState } from "@/state/chatbot-state.js";
import { DEFAULT_SECONDARY_COLOR } from "@/config.js";

export const ChatBotHeader = () => {
  const botGuid = useChatbotState((state) => state.botGuid);
  const setOpen = useChatbotState((state) => state.setOpen);

  const { data: botData } = useGetBotData(botGuid);

  return (
    <CardHeader
      className="relative bg-[var(--bgcolor)] w-full p-4 pl-6 rounded-t-md cursor-pointer"
      style={{
        '--bgcolor': botData?.configuration?.secondary_color || DEFAULT_SECONDARY_COLOR
      }}
      onClick={() => setOpen(false)}
    >
      <CardTitle className="text-white text-base w-full">
        <div className="flex items-center w-full">
          <BotAvatar url={botData.logo_url} name={botData.name} />
          <div className="w-full ml-2 flex items-center">
            {botData.name}
          </div>
        </div>
      </CardTitle>
      <PopoverClose asChild>
        <Button className="bg-closeBtn rounded-full hover:bg-closeBtn w-8 h-8 p-1 aspect-square mt-1 absolute -right-4 -top-4 !shadow-md">
          <CloseIcon className="w-4 h-4 text-white" />
        </Button>
      </PopoverClose>
    </CardHeader>
  )
}
