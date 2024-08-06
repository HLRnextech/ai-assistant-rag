import React, { useEffect, useState } from "react";
import { Popover, PopoverTrigger, PopoverContent } from '@/components/ui/popover.jsx';
import { Button } from '@/components/ui/button.jsx';
import ChatbotBody from '@/components/chatbot-body.jsx';
import ChatIcon from '@/assets/chat.svg';

import { getBotGuid, isLocalStorageAvailable } from '@/lib/utils';
import { useGetBotData } from '@/hooks/useGetBotData';

import { useChatbotState } from '@/state/chatbot-state.js';
import Tooltip from "./tooltip.jsx";
import { TOOLTIP_DISMISSED_KEY_LOCAL_STORAGE, DEFAULT_SECONDARY_COLOR } from "@/config.js";

const Chatbot = () => {
  const [tooltipLSSync, setTooltipLSSync] = useState(false);
  const open = useChatbotState((state) => state.open);
  const tooltipDismissed = useChatbotState((state) => state.tooltipDismissed);
  const setOpen = useChatbotState((state) => state.setOpen);
  const botGuid = useChatbotState((state) => state.botGuid);
  const setBotGuid = useChatbotState((state) => state.setBotGuid);
  const setTooltipDismissed = useChatbotState((state) => state.setTooltipDismissed);
  const clearSessionEndTimer = useChatbotState(state => state.clearSessionEndTimer)
  const clearFeedbackTimer = useChatbotState(state => state.clearFeedbackTimer)
  const setTrackInactivity = useChatbotState(state => state.setTrackInactivity)

  const { data } = useGetBotData(botGuid);

  useEffect(() => {
    if (isLocalStorageAvailable()) {
      const tooltipDismissedLS = localStorage.getItem(TOOLTIP_DISMISSED_KEY_LOCAL_STORAGE);
      if (tooltipDismissedLS === 'true') {
        setTooltipDismissed(true);
      }
      setTooltipLSSync(true);
    }
  }, [])

  useEffect(() => {
    if (!open) {
      clearFeedbackTimer();
      clearSessionEndTimer();
    }

    setTrackInactivity(false)
  }, [open])

  useEffect(() => {
    if (open && !tooltipDismissed) {
      setTooltipDismissed(true);
    }
  }, [open, tooltipDismissed])

  useEffect(() => {
    if (botGuid) {
      return;
    }

    const guid = getBotGuid();
    if (!guid) {
      console.error('Bot GUID not found');
      return;
    }
    setBotGuid(guid);
  }, []);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          disabled={!data}
          className="fixed bottom-2 right-2 bg-[var(--bgcolor)] hover:bg-[var(--bgcolor)] rounded-full w-11 h-11 p-1 aspect-square disabled:opacity-70"
          style={{
            '--bgcolor': data?.configuration?.secondary_color || DEFAULT_SECONDARY_COLOR
          }}
        >
          <ChatIcon alt="Chatbot icon" />
        </Button>
      </PopoverTrigger>
      {
        tooltipLSSync && !tooltipDismissed && !open &&
        data && data.configuration && data.configuration.greeting_message &&
        <Tooltip
          content={data.configuration.greeting_message}
          onClose={() => setTooltipDismissed(true)}
          onTooltipClick={() => setOpen(true)}
        />
      }
      <PopoverContent
        className="h-full w-full p-0 m-0 rounded-full border-none shadow-none"
        side="top"
        align="end"
        avoidCollisions={false}
        onInteractOutside={(e) => {
          if (open) {
            e.preventDefault();
          }
        }}
      >
        <ChatbotBody />
      </PopoverContent>
    </Popover>
  )
}

export default Chatbot;
