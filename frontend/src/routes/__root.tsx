import type { ReactNode } from 'react';

import {
  createRootRoute,
  HeadContent,
  Outlet,
  Scripts,
} from '@tanstack/react-router';

import { AppShell } from '#/components';
import { QueryProvider } from '#/providers/QueryProvider';
import { TraderSelectionProvider } from '#/providers/TraderSelectionProvider';

import '#/styles/fonts.css';
import '#/styles/variables.css';
import '#/styles/globals.css';

export const Route = createRootRoute({
  head: () => ({
    meta: [
      {
        charSet: 'utf-8',
      },
      {
        name:    'viewport',
        content: 'width=device-width, initial-scale=1',
      },
      {
        title: 'Escape Protocol',
      },
      {
        name:    'description',
        content: 'Escape from Tarkov ARG',
      },
    ],
  }),

  component: RootComponent,
});

function RootComponent() {
  return (
    <RootDocument>
      <QueryProvider>
        <TraderSelectionProvider>
          <AppShell>
            <Outlet />
          </AppShell>
        </TraderSelectionProvider>
      </QueryProvider>
    </RootDocument>
  );
}

function RootDocument({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="ru">
      <head>
        <HeadContent />
      </head>

      <body>
        {children}

        <Scripts />
      </body>
    </html>
  );
}
