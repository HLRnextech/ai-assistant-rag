import React, { useEffect, useMemo, useState, useRef } from "react";
import { AlertCircle, RotateCcw } from "lucide-react"
import { useQueryClient } from "@tanstack/react-query";

import { Card, CardContent, CardFooter } from "@/components/ui/card.jsx";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert.jsx";
import { ChatBotHeader } from './chatbot-header.jsx';
import { TextareaWithAccessory } from "@/components/ui/text-area-with-accessory.jsx";
import { SubmitBtn } from "@/components/submit-btn.jsx";
import ChatbotMessages from "@/components/chatbot-messages.jsx";
import { Button } from "@/components/ui/button.jsx";

import { useChatbotState } from "@/state/chatbot-state.js";
import { captureException, debounce, generateGuid, isLocalStorageAvailable } from "@/lib/utils.js";
import { useCreateSession } from "@/hooks/useCreateSession.js";
import { useGetMessages } from "@/hooks/useGetMessages.js";
import { useGetBotData } from "@/hooks/useGetBotData.js";
import { useGetSessionStatus } from "@/hooks/useGetSessionStatus.js";
import { useThrottledEffect } from "@/hooks/useThrottledEffect.js";
import { usePrevious } from "@/hooks/usePrevious.js";
import { useTriggerBotMessage } from "@/hooks/useTriggerBotMessage.js";
import { useEndSession } from "@/hooks/useEndSession.js";
import {
  INITIAL_SCROLL_DELAY_MS,
  SCROLL_THROTTLE_MS,
  CHAT_PLACEHOLDER,
  TMP_MSG_SYMBOL,
  DEFAULT_ERROR_ON_SEND_MSG,
  DEFAULT_ERROR_ON_SESSION_INACTIVE,
  DEFAULT_END_SESSION_CONFIRM_MSG,
  DEFAULT_FEEDBACK_REQUEST_MSG,
  API_BASE_URL,
  DEFAULT_GOODBYE_MESSAGE,
  SESSION_GUID_KEY_LOCAL_STORAGE,
  DEFAULT_STATIC_DISCLAIMER
} from "@/config.js";

import CloseIcon from "@/assets/close.svg";

let autoScroll = false;

const ChatbotBody = () => {
  const queryClient = useQueryClient()
  const msgContainerRef = useRef(null);
  const [isFirstTokenReceived, setIsFirstTokenReceived] = useState(false);
  const [inputMessage, setInputMessage] = useState("");
  const [endingSession, setEndingSession] = useState(false);

  const trackInactivity = useChatbotState(state => state.trackInactivity)
  const resetChat = useChatbotState(state => state.resetChat)
  const btnTypeEndSession = useChatbotState(state => state.btnTypeEndSession)
  const setBtnTypeEndSession = useChatbotState(state => state.setBtnTypeEndSession)
  const setOrCreateUserGuid = useChatbotState(state => state.setOrCreateUserGuid)
  const setSessionGuid = useChatbotState(state => state.setSessionGuid)
  const userGuid = useChatbotState(state => state.userGuid)
  const sessionGuid = useChatbotState(state => state.sessionGuid)
  const botGuid = useChatbotState(state => state.botGuid)
  const isMsgStreaming = useChatbotState(state => state.isMsgStreaming)
  const setIsMsgStreaming = useChatbotState(state => state.setIsMsgStreaming)
  const getMessageByGuid = useChatbotState(state => state.getMessageByGuid)
  const appendTokensForMessage = useChatbotState(state => state.appendTokensForMessage)
  const appendMessage = useChatbotState(state => state.appendMessage)
  const removeMessageByGuid = useChatbotState(state => state.removeMessageByGuid)
  const removeTmpSymbolFromMessage = useChatbotState(state => state.removeTmpSymbolFromMessage)
  const updateMessageGuid = useChatbotState(state => state.updateMessageGuid)
  const messages = useChatbotState(state => state.messages)
  const errorMessage = useChatbotState(state => state.errorMessage)
  const setErrorMessage = useChatbotState(state => state.setErrorMessage)
  const setFeedbackTimer = useChatbotState(state => state.setFeedbackTimer)
  const clearFeedbackTimer = useChatbotState(state => state.clearFeedbackTimer)
  const setSessionEndTimer = useChatbotState(state => state.setSessionEndTimer)
  const clearSessionEndTimer = useChatbotState(state => state.clearSessionEndTimer)
  const setTrackInactivity = useChatbotState(state => state.setTrackInactivity)

  const previousSessionGuid = usePrevious(sessionGuid)

  const {
    data: botData,
    isLoading: botDataLoading
  } = useGetBotData(botGuid)
  const { mutate: createSession, isError: createSessionError } = useCreateSession()
  const {
    data: sessionStatus,
    isPending: sessionStatusPending,
    isLoading: sessionStatusLoading,
    isError: sessionStatusError,
    refetch: refetchSessionStatus
  } = useGetSessionStatus(botGuid, sessionGuid, userGuid)
  const {
    isError: getMessagesError
  } = useGetMessages(botGuid, sessionGuid, userGuid)

  const {
    mutateAsync: triggerBotMessage
  } = useTriggerBotMessage()
  const {
    mutateAsync: endSession
  } = useEndSession()

  const isSubmitDisabled = useMemo(() =>
    sessionStatusPending || sessionStatusLoading || sessionStatusError || sessionStatus?.status !== "active" ||
    botDataLoading || botData?.status !== "success"
    || inputMessage.trim().length === 0 || isMsgStreaming,
    [sessionStatusPending, sessionStatusLoading, sessionStatusError, botDataLoading, sessionStatus, isMsgStreaming, inputMessage]
  )

  const isEndSessionDisabled = useMemo(() =>
    sessionStatusPending || sessionStatusLoading || botDataLoading || isMsgStreaming || endingSession,
    [sessionStatusPending, sessionStatusLoading, botDataLoading, isMsgStreaming, endingSession]
  )

  useEffect(() => {
    setOrCreateUserGuid()
  }, [])

  useEffect(() => {
    if (sessionStatusLoading || sessionStatusPending) return;

    if (sessionStatus?.status !== "active") {
      setErrorMessage(DEFAULT_ERROR_ON_SESSION_INACTIVE)
      setBtnTypeEndSession('reset_chat');
    }
  }, [sessionStatus, sessionStatusLoading, sessionStatusPending])

  useEffect(() => {
    if (!userGuid || !botData) {
      return
    }

    if (botData.status !== "success") {
      return
    }

    let generateNewSession = true

    if (isLocalStorageAvailable()) {
      const sessionGuidInLocalStorage = localStorage.getItem(SESSION_GUID_KEY_LOCAL_STORAGE)
      if (sessionGuidInLocalStorage) {
        setSessionGuid(sessionGuidInLocalStorage)
        generateNewSession = false
      }
    }

    if (generateNewSession) {
      createSession({ botGuid, userGuid })
    }
  }, [userGuid, botData])

  useEffect(() => {
    // when chat is reset, there is a brief moment when current session guid is empty and previous session guid is the last session guid
    if (!sessionGuid && previousSessionGuid) {
      queryClient.removeQueries({
        queryKey: ["bot", ""]
      })
      queryClient.removeQueries({
        queryKey: ["messages", "bot", botGuid, "session", previousSessionGuid]
      })
      queryClient.removeQueries({
        queryKey: ["messages", "bot", botGuid, "session", ""]
      })

      queryClient.removeQueries({
        queryKey: ["bot", botGuid, "session", "status", previousSessionGuid]
      })
      queryClient.removeQueries({
        queryKey: ["bot", botGuid, "session", "status", ""]
      })
    }
  }, [sessionGuid, previousSessionGuid])

  useEffect(() => {
    if (!msgContainerRef.current) return;

    let lastScroll = 0;
    let lastScrollDirection = "down";

    function handleScroll() {
      debounce(() => {
        if (!msgContainerRef.current) return;

        let currentScroll = msgContainerRef.current.scrollTop || msgContainerRef.current.scrollTop;

        if (currentScroll > 0 && lastScroll <= currentScroll) {
          lastScroll = currentScroll;

          if (lastScrollDirection !== "down") {
            onScrollDirectionChange(lastScrollDirection, "down")
            lastScrollDirection = "down";
          }
        } else {
          lastScroll = currentScroll;

          if (lastScrollDirection !== "up") {
            onScrollDirectionChange(lastScrollDirection, "up")
            lastScrollDirection = "up";
          }
        }
      }, 50)
    }

    msgContainerRef.current.addEventListener("scroll", handleScroll);

    return () => {
      msgContainerRef.current?.removeEventListener("scroll", handleScroll);
    }
  }, [msgContainerRef])

  useEffect(() => {
    if (messages.length === 0 || !trackInactivity) {
      return;
    }

    const lastMessage = messages[messages.length - 1];

    if (lastMessage.role === "bot" && !lastMessage.cfg_type && !(TMP_MSG_SYMBOL in lastMessage)) {
      if (sessionStatus && typeof sessionStatus.feedback === 'number') {
        // skip setting feedback timer if feedback is already provided
        clearFeedbackTimer();
        // directly set the session end timer
        setSessionEndTimer(
          () => {
            // call the handleEndSession function
            handleEndSession(null, false, ['goodbye_message'])
          }
        )
        return
      }

      setFeedbackTimer(
        () => {
          // trigger a feedback request message
          triggerBotMessage({
            userGuid,
            messageType: "feedback_requested_message",
            sessionGuid
          })

          setSessionEndTimer(
            () => {
              // call the handleEndSession function
              handleEndSession(null, false, ['goodbye_message'])
            }
          )
        }
      );
    }
  }, [messages, trackInactivity, sessionStatus])

  const onScrollDirectionChange = (prevScrollDirection, currentScrollDirection) => {
    if (prevScrollDirection === currentScrollDirection) {
      return;
    }

    if (prevScrollDirection === "down" && currentScrollDirection === "up") {
      // the user intervened and scrolled up
      // disable auto-scrolling to bottom when the current msg is being streamed
      autoScroll = false;
    }
  }

  const scrollToBottom = (force = false) => {
    if (!msgContainerRef.current) return;

    if (force || autoScroll) {
      msgContainerRef.current.scrollTo({
        top: msgContainerRef.current.scrollHeight,
        behavior: "smooth"
      });
    }
  }

  const handleEndSession = async (e = null, showConfirmDialog = true, msgTypeTriggers = ['feedback_requested_message', 'goodbye_message']) => {
    e?.preventDefault();

    if (isMsgStreaming || endingSession) return;

    clearFeedbackTimer();
    clearSessionEndTimer();

    if (showConfirmDialog && !window.confirm(DEFAULT_END_SESSION_CONFIRM_MSG)) {
      return;
    }

    setEndingSession(true);

    if (msgTypeTriggers.includes('feedback_requested_message')) {
      try {
        // 1. trigger feedback_requested_message from the api
        // 2. on success of the above, push the feedback message to zustand state
        await triggerBotMessage({
          userGuid,
          messageType: "feedback_requested_message",
          sessionGuid
        })
      } catch (error) {
        console.error('error triggering feedback_requested_message:', error);
        appendMessage({
          guid: generateGuid(),
          role: "bot",
          type: "text",
          content: botData?.configuration?.feedback_message || DEFAULT_FEEDBACK_REQUEST_MSG,
          created_at: new Date().toISOString(),
          feedback: null,
          cfg_type: "feedback_requested_message"
        })
      }
    }

    if (msgTypeTriggers.includes('goodbye_message')) {
      try {
        // 3. trigger goodbye_message from the api
        // 4. on success of the above, push the goodbye message to zustand state
        await triggerBotMessage({
          userGuid,
          messageType: "goodbye_message",
          sessionGuid
        })
      } catch (error) {
        console.error('error triggering goodbye_message:', error);
        appendMessage({
          guid: generateGuid(),
          role: "bot",
          type: "text",
          content: botData?.configuration?.goodbye_message || DEFAULT_GOODBYE_MESSAGE,
          created_at: new Date().toISOString(),
          feedback: null,
          cfg_type: "goodbye_message"
        })
      }
    }


    try {
      // 5. make the end session api call
      await endSession({ userGuid, sessionGuid, botGuid })
      refetchSessionStatus()
    } catch (error) {
      console.error('error ending session:', error);
      // TODO: force end session
    }

    setEndingSession(false);
    scrollToBottom(true);
    // 7. update the end session btn icon to a reset icon
    setBtnTypeEndSession('reset_chat');
  }

  const handleResetChat = async (e) => {
    // 8. when the user clicks the btn again, reset the chat state by clearing out zustand state, react query cache and local storage
    e?.preventDefault();

    resetChat();
    setInputMessage('');
    queryClient.removeQueries({
      queryKey: ["messages"],
      stale: true,
    })

    createSession({
      botGuid,
      userGuid
    })
  }

  const handleFormSubmit = async (e) => {
    e?.preventDefault();
    if (isMsgStreaming) return;

    const encoded = encodeURIComponent(inputMessage);
    const url = new URL(`/session/answer_question/${sessionGuid}`, API_BASE_URL);
    url.searchParams.append("question", encoded);
    url.searchParams.append("user_guid", userGuid);

    setIsMsgStreaming(true);
    setIsFirstTokenReceived(false);
    setErrorMessage('');
    autoScroll = true;

    const tmpUserMessageGuid = generateGuid();
    let tmpBotMessageGuid = null;

    const userMsg = {
      guid: tmpUserMessageGuid,
      role: "user",
      type: "text",
      content: inputMessage,
      feedback: null,
      created_at: new Date().toISOString(),
      [TMP_MSG_SYMBOL]: true
    }
    appendMessage(userMsg);
    setTimeout(() => scrollToBottom(true), INITIAL_SCROLL_DELAY_MS);

    try {
      const source = new EventSource(url);
      tmpBotMessageGuid = generateGuid();

      source.onmessage = function (event) {
        try {
          const data = JSON.parse(event.data);
          if ("bot_message_guid" in data && "user_message_guid" in data) {
            source.close();
            updateMessageGuid(tmpBotMessageGuid, data.bot_message_guid);
            removeTmpSymbolFromMessage(data.bot_message_guid);

            updateMessageGuid(tmpUserMessageGuid, data.user_message_guid);
            removeTmpSymbolFromMessage(data.user_message_guid);
            setIsMsgStreaming(false);
            setInputMessage('');
            setTrackInactivity(true);
          } else if ("token" in data) {
            setIsFirstTokenReceived(true);

            if (getMessageByGuid(tmpBotMessageGuid)) {
              appendTokensForMessage(tmpBotMessageGuid, data.token);
            } else {
              const botMsg = {
                guid: tmpBotMessageGuid,
                role: "bot",
                type: "text",
                content: data.token,
                feedback: null,
                created_at: new Date().toISOString(),
                [TMP_MSG_SYMBOL]: true
              }

              appendMessage(botMsg);
            }
          } else {
            throw new Error(`Invalid data: ${data}`);
          }
        } catch (error) {
          captureException(error, {
            sessionGuid,
            question: inputMessage,
            userGuid
          });

          console.error(error);
          source.close();
          setIsMsgStreaming(false);
          setIsFirstTokenReceived(false);

          const existingBotMsg = getMessageByGuid(tmpBotMessageGuid);
          if (!existingBotMsg) {
            removeMessageByGuid(tmpUserMessageGuid);
          }
          setErrorMessage(DEFAULT_ERROR_ON_SEND_MSG)
        }
      };

      source.onerror = function (event) {
        captureException(new Error(`EventSource onerror: ${event}`), {
          sessionGuid,
          question: inputMessage,
          userGuid
        });
        console.error('Error:', event);
        source.close();
        setIsMsgStreaming(false);
        setIsFirstTokenReceived(false);
        const existingBotMsg = getMessageByGuid(tmpBotMessageGuid);
        if (!existingBotMsg) {
          removeMessageByGuid(tmpUserMessageGuid);
        }
        setErrorMessage(DEFAULT_ERROR_ON_SEND_MSG)
      };
    } catch (error) {
      captureException(error, {
        sessionGuid,
        question: inputMessage,
        userGuid
      });
      console.error(error);
      setIsMsgStreaming(false);
      setIsFirstTokenReceived(false);
      const existingBotMsg = getMessageByGuid(tmpBotMessageGuid);
      if (!existingBotMsg) {
        removeMessageByGuid(tmpUserMessageGuid);
      }
      setErrorMessage(DEFAULT_ERROR_ON_SEND_MSG)
    }
  };

  useThrottledEffect(() => {
    if (!msgContainerRef.current) return;

    scrollToBottom();
  }, SCROLL_THROTTLE_MS, [messages])

  const handleTextInputChange = (e) =>
    setInputMessage(e.target.value);

  const handleInputKeyDown = async (event) => {
    clearFeedbackTimer();
    clearSessionEndTimer();

    const isEnterKey = event?.key === "Enter";
    const isShiftPressed = !!event?.shiftKey;

    if (!isEnterKey || isShiftPressed) return;

    if (isSubmitDisabled) {
      return;
    }
    await handleFormSubmit(event);
  };

  return (
    <Card className="flex flex-col gap-4 w-[28rem]">
      <ChatBotHeader />
      <CardContent
        className={`flex flex-col gap-5 h-72 overflow-y-auto overflow-x-hidden ${(botData?.status !== "success" || createSessionError || sessionStatusError || getMessagesError) ? 'justify-end' : ''}`}
        ref={msgContainerRef}
      >
        {
          (botData?.status !== "success" || createSessionError || sessionStatusError) ?
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Heads up!</AlertTitle>
              <AlertDescription>
                {
                  createSessionError ?
                    'We encountered some issue while setting up this bot. Please try again later.'
                    :
                    (
                      sessionStatusError ?
                        'We are unable to setup this conversation. Please start a new conversation.'
                        :
                        `This bot is in ${botData?.status} state. You can only interact with the bot when it is in success state.`
                    )
                }
              </AlertDescription>
            </Alert>
            :
            <ChatbotMessages
              isMsgStreaming={isMsgStreaming}
              isFirstTokenReceived={isFirstTokenReceived}
              scrollToBottom={scrollToBottom}
            />
        }
      </CardContent>
      <CardFooter>
        <div className="flex flex-col w-full gap-4">
          <form className="flex gap-5 w-full" onSubmit={handleFormSubmit}>
            <div className="flex-col flex-1">
              <TextareaWithAccessory
                className={`h-20 ${errorMessage ? 'border border-destructive' : ''}`}
                onChange={handleTextInputChange}
                doNotResize
                placeholder={CHAT_PLACEHOLDER}
                value={inputMessage}
                onKeyDown={handleInputKeyDown}
                autoFocus
              >
                <SubmitBtn onClick={handleFormSubmit} disabled={isSubmitDisabled} bgcolor={botData?.configuration?.secondary_color} />
                <Button
                  type="button"
                  disabled={isEndSessionDisabled}
                  onClick={btnTypeEndSession === 'end_session' ? handleEndSession : handleResetChat}
                  className={`${btnTypeEndSession === 'end_session' ? 'bg-red-400 hover:bg-red-500' : 'bg-green-400 hover:bg-green-400'} rounded-full disabled:opacity-70 mt-1 w-8 h-8 ml-2 p-1 aspect-square`}
                >
                  {
                    btnTypeEndSession === 'end_session' ?
                      <CloseIcon className="w-4 h-4 text-white" />
                      :
                      <RotateCcw className="w-4 h-4 text-white" />
                  }
                </Button>
              </TextareaWithAccessory>
              <span
                className={`text-destructive text-xs block`}
              >
                {errorMessage}
              </span>
            </div>
          </form>
          <p className="w-full text-xs text-subhead">
            {DEFAULT_STATIC_DISCLAIMER}
            <br />
            {
              (botData &&
                botData.configuration &&
                botData.configuration.disclaimer_message)
                ? botData.configuration.disclaimer_message : ''
            }
          </p>
        </div>
      </CardFooter>
    </Card>
  )
}

export default ChatbotBody;
