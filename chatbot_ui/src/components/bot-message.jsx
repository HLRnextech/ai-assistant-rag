import React, { useEffect, useState } from "react";
import { ThumbsUpIcon } from "lucide-react";
import { ThumbsDownIcon } from "lucide-react";

import { StarRating } from "@/components/star-rating.jsx";
import BotAvatar from "@/components/bot-avatar.jsx";
import { Button } from "@/components/ui/button.jsx";
import { TMP_MSG_SYMBOL } from "@/config.js";
import { useChatbotState } from "@/state/chatbot-state.js";
import { useSendMessageFeedback } from "@/hooks/useSendMessageFeedback.js";
import { useGetBotData } from "@/hooks/useGetBotData.js";
import { useGetSessionStatus } from "@/hooks/useGetSessionStatus";
import { useSendSessionFeedback } from "@/hooks/useSendSessionFeedback";

const BotMessage = ({ message }) => {
  const [sessionRating, setSessionRating] = useState(0)
  const {
    mutate: sendFeedback,
    isPending: isMessageFeedbackPending,
  } = useSendMessageFeedback()
  const {
    mutate: sendSessionFeedback,
    isPending: isSessionFeedbackPending
  } = useSendSessionFeedback()
  const userGuid = useChatbotState(state => state.userGuid)
  const sessionGuid = useChatbotState(state => state.sessionGuid)
  const botGuid = useChatbotState(state => state.botGuid)

  const { data: botData } = useGetBotData(botGuid);
  const { data: sessionStatus } = useGetSessionStatus(botGuid, sessionGuid, userGuid)

  useEffect(() => {
    if (sessionStatus?.feedback) {
      setSessionRating(sessionStatus.feedback)
    }
  }, [sessionStatus])

  const handleClick = (feedback) => {
    if (isMessageFeedbackPending || TMP_MSG_SYMBOL in message) return
    let _feedback = feedback;

    if (feedback === message.feedback) {
      _feedback = null;
    }

    sendFeedback({
      sessionGuid,
      messageGuid: message.guid,
      userGuid,
      feedback: _feedback,
      botGuid
    })
  }

  const handleSessionRatingChange = (rating) => {
    if (isSessionFeedbackPending) return

    let _rating = rating;
    if (rating === sessionStatus?.feedback) {
      _rating = null;
    }

    setSessionRating(_rating || 0)
    sendSessionFeedback({
      sessionGuid,
      userGuid,
      feedback: _rating,
      botGuid
    })
  }

  return (
    <div
      className="flex gap-2 items-end w-fit max-w-[90%]"
    >
      <BotAvatar
        url={botData.logo_url}
        name={botData.name}
      />
      <div
        className={
          "grid grid-cols-1 bg-chatSystemMessage text-chatSystemMessageText rounded-xl rounded-bl-none p-4 h-fit"
        }
      >
        <div className="col-span-1">
          <pre className="font-sans whitespace-break-spaces">{message.content}</pre>

          {
            !(TMP_MSG_SYMBOL in message) && !message.cfg_type &&
            <div className="flex items-center gap-4 pt-2">
              <Button
                title="Upvote"
                variant="ghost"
                size="icon"
                className={
                  `disabled:cursor-not-allowed w-4 h-4 hover:bg-transparent ${message.feedback === 'positive' ? 'text-stone-900' : 'text-stone-400'} hover:text-stone-900`
                }
                disabled={isSessionFeedbackPending}
                onClick={() => handleClick('positive')}
              >
                <ThumbsUpIcon className="w-4 h-4" />
              </Button>

              <Button
                title="Downvote"
                variant="ghost"
                size="icon"
                className={
                  `disabled:cursor-not-allowed w-4 h-4 hover:bg-transparent ${message.feedback === 'negative' ? 'text-stone-900' : 'text-stone-400'} hover:text-stone-900`
                }
                disabled={isSessionFeedbackPending}
                onClick={() => handleClick('negative')}
              >
                <ThumbsDownIcon className="w-4 h-4" />
              </Button>
            </div>
          }
          {
            message.cfg_type && message.cfg_type === "feedback_requested_message" &&
            <div className="flex items-center gap-4 pt-2">
              <StarRating
                rating={sessionRating}
                onRatingChange={handleSessionRatingChange}
              />
            </div>
          }
        </div>
      </div>
    </div>
  );
};

export default BotMessage;
