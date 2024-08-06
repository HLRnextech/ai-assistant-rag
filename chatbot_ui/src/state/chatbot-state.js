import { create } from 'zustand'

import { generateGuid, isLocalStorageAvailable } from '@/lib/utils'
import {
  SESSION_GUID_KEY_LOCAL_STORAGE,
  USER_GUID_KEY_LOCAL_STORAGE,
  TOOLTIP_DISMISSED_KEY_LOCAL_STORAGE,
  TMP_MSG_SYMBOL,
  DEFAULT_FEEDBACK_TIMER_DURATION_MS,
  DEFAULT_END_SESSION_TIMER_DURATION_MS
} from '@/config'

export const useChatbotState = create((set, get) => ({
  open: false,
  tooltipDismissed: false,
  errorMessage: '',
  botGuid: '',
  userGuid: '',
  sessionGuid: '',
  isMsgStreaming: false,
  messages: [],
  btnTypeEndSession: 'end_session',
  trackInactivity: false,
  feedbackTimer: null,
  endSessionTimer: null,
  setTrackInactivity: (t) => set(() => ({ trackInactivity: t })),
  setSessionEndTimer: (cb) => set(() => {
    if (get().endSessionTimer) {
      console.log('clearing existing end session timer')
      clearTimeout(get().endSessionTimer)
    }
    console.log('setting new end session timer')
    const timer = setTimeout(cb, DEFAULT_END_SESSION_TIMER_DURATION_MS)
    return { endSessionTimer: timer }
  }),
  clearSessionEndTimer: () => set(() => {
    if (get().endSessionTimer) {
      console.log('clearing end session timer')
      clearTimeout(get().endSessionTimer)
    }
    return { endSessionTimer: null }
  }),
  setFeedbackTimer: (cb) => set(() => {
    if (get().feedbackTimer) {
      console.log('clearing existing feedback timer')
      clearTimeout(get().feedbackTimer)
    }
    console.log('setting new feedback timer')
    const timer = setTimeout(cb, DEFAULT_FEEDBACK_TIMER_DURATION_MS)
    return { feedbackTimer: timer }
  }),
  clearFeedbackTimer: () => set(() => {
    if (get().feedbackTimer) {
      console.log('clearing feedback timer')
      clearTimeout(get().feedbackTimer)
    }
    return { feedbackTimer: null }
  }),
  setBtnTypeEndSession: (btnType) => set(() => ({ btnTypeEndSession: btnType })),
  setErrorMessage: (e) => set(() => ({ errorMessage: e })),
  setTooltipDismissed: (d) => set(() => {
    if (isLocalStorageAvailable()) {
      localStorage.setItem(TOOLTIP_DISMISSED_KEY_LOCAL_STORAGE, d.toString());
    }
    return { tooltipDismissed: d }
  }),
  setMessages: (m) => set(() => ({ messages: m })),
  getMessageByGuid: (guid) => {
    const message = get().messages.find((m) => m.guid === guid)
    return message
  },
  updateMessageGuid: (originalGuid, newGuid) => set((state) => {
    const messages = state.messages.map((m) => {
      if (m.guid === originalGuid) {
        return { ...m, guid: newGuid }
      }
      return m
    })
    return { messages }
  }),
  removeTmpSymbolFromMessage: (guid) => set((state) => {
    const messages = [...state.messages]
    const message = messages.find((m) => m.guid === guid)
    if (message && TMP_MSG_SYMBOL in message) {
      delete message[TMP_MSG_SYMBOL]
    }
    return { messages }
  }),
  setMessageFeedback: (messageGuid, feedback) => set((state) => {
    const messages = state.messages.map((m) => {
      if (m.guid === messageGuid) {
        return { ...m, feedback }
      }
      return m
    })
    return { messages }
  }),
  appendMessage: (m) => set((state) => {
    const messages = [...state.messages, m]
    return { messages }
  }),
  removeMessageByGuid: (guid) => set((state) => {
    const messages = state.messages.filter((m) => m.guid !== guid)
    return { messages }
  }),
  appendTokensForMessage: (messageGuid, token) => set((state) => {
    const messages = state.messages.map((m) => {
      if (m.guid === messageGuid) {
        return { ...m, content: m.content + token }
      }
      return m
    })
    return { messages }
  }),
  setIsMsgStreaming: (s) => set(() => ({ isMsgStreaming: s })),
  setBotGuid: (guid) => set(() => ({ botGuid: guid })),
  setOrCreateUserGuid: () => {
    set((state) => {
      if (state.userGuid) {
        return { userGuid: state.userGuid }
      }
      let userGuid = ''
      if (isLocalStorageAvailable()) {
        userGuid = localStorage.getItem(USER_GUID_KEY_LOCAL_STORAGE)
        if (!userGuid) {
          userGuid = generateGuid()
          localStorage.setItem(USER_GUID_KEY_LOCAL_STORAGE, userGuid)
        }
      }

      if (!userGuid) {
        userGuid = generateGuid()
      }

      return { userGuid }
    })
  },
  setSessionGuid: (guid) => {
    set(() => {
      if (isLocalStorageAvailable()) {
        localStorage.setItem(SESSION_GUID_KEY_LOCAL_STORAGE, guid)
      }
      return { sessionGuid: guid }
    })
  },
  setOpen: (o) => set(() => ({ open: o })),
  resetChat: () => set(() => {
    if (isLocalStorageAvailable()) {
      localStorage.removeItem(SESSION_GUID_KEY_LOCAL_STORAGE)
    }
    if (get().feedbackTimer) {
      clearTimeout(get().feedbackTimer)
    }
    if (get().endSessionTimer) {
      clearTimeout(get().endSessionTimer)
    }

    return {
      btnTypeEndSession: 'end_session',
      errorMessage: '',
      sessionGuid: '',
      messages: [],
      isMsgStreaming: false,
      feedbackTimer: null,
      endSessionTimer: null,
      trackInactivity: false
    }
  }),
}))
