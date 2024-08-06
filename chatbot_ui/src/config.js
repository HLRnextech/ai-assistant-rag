export const IS_PROD = process.env.NODE_ENV === 'production';
export const API_BASE_URL = process.env.API_BASE_URL;
export const SESSION_GUID_KEY_LOCAL_STORAGE = 'sessionGuid';
export const USER_GUID_KEY_LOCAL_STORAGE = 'userGuid';
export const TOOLTIP_DISMISSED_KEY_LOCAL_STORAGE = 'tooltipDismissed';
export const CHAT_PLACEHOLDER = 'Type your message here...';
export const DEFAULT_ERROR_ON_SEND_MSG = 'Cannot send your message. Please check the message and try again. If the problem persists, please contact admin.';
export const DEFAULT_ERROR_ON_SESSION_INACTIVE = 'You cannot send message to this conversation as it not active. Please start a new conversation.';
export const DEFAULT_END_SESSION_CONFIRM_MSG = 'Are you sure you want to end this conversation?'
export const DEFAULT_FEEDBACK_REQUEST_MSG = 'Please provide your feedback.'
export const DEFAULT_GOODBYE_MESSAGE = 'Thank you for your time. Have a great day!'
export const DEFAULT_STATIC_DISCLAIMER = 'This is an AI system powered by Nextech.'

export const INITIAL_SCROLL_DELAY_MS = 100;
export const SCROLL_THROTTLE_MS = 250;
export const DEFAULT_FEEDBACK_TIMER_DURATION_MS = 30 * 1000; // 30 seconds
export const DEFAULT_END_SESSION_TIMER_DURATION_MS = 60 * 1000; // 60 seconds
export const TMP_MSG_SYMBOL = Symbol('is_tmp');

export const DEFAULT_SECONDARY_COLOR = '#2150e0';