import { clsx } from "clsx"
import { twMerge } from "tailwind-merge"
import { v4 as uuidv4 } from "uuid"
import * as Sentry from "@sentry/react"

import { IS_PROD } from "@/config"

export const cn = (...inputs) => {
  return twMerge(clsx(inputs))
}

export const getBotGuid = () => {
  if (IS_PROD) {
    const script = document.querySelector('script[data-nb-guid]');
    if (script) {
      return script.getAttribute('data-nb-guid');
    }
  } else {
    const botGuid = new URLSearchParams(window.location.search).get('bot_guid');

    if (botGuid) {
      return botGuid;
    }
  }
}

export const isLocalStorageAvailable = () => {
  try {
    const key = '__storage_test__';
    localStorage.setItem(key, key);
    localStorage.removeItem(key);
    return true;
  } catch (e) {
    return false;
  }
}

export const generateGuid = () => {
  const uuid = uuidv4()
  return uuid.replace(/-/g, '')
}

export const debounce = (method, delay) => {
  clearTimeout(method._tId);
  method._tId = setTimeout(function () {
    method();
  }, delay);
}

export const captureException = (error, metadata = undefined) => {
  if (metadata) {
    Sentry.withScope(scope => {
      scope.setExtras(metadata)
      Sentry.captureException(error)
    })
  } else {
    Sentry.captureException(error)
  }
}
