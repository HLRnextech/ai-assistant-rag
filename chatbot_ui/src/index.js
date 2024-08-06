import React from 'react';
import ReactDOM from 'react-dom/client';
import * as Sentry from "@sentry/react";

import {
  QueryClient,
  QueryClientProvider,
} from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'

import './index.css';

import { IS_PROD } from '@/config';
import Chatbot from '@/components/chatbot.jsx';

Sentry.init({
  dsn: process.env.SENTRY_DSN,
  environment: process.env.NODE_ENV,
});

const queryClient = new QueryClient()

const App = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <ReactQueryDevtools initialIsOpen={false} buttonPosition='bottom-left' />
      <Chatbot />
    </QueryClientProvider>
  );
};

let container = document.getElementById('root');

if (IS_PROD && !container) {
  container = document.createElement('div');
  container.id = 'root';
  document.body.appendChild(container);
}

const root = ReactDOM.createRoot(container);
root.render(<App />);
