import type { ReactNode } from 'react';

import { useEffect, useState } from 'react';

import { Footer } from '#/features/footer/Footer';
import { Header } from '#/features/header/Header';
import { LoadingScreen } from '#/features/loading-screen/LoadingScreen';

import classes from './AppShell.module.css';

interface AppShellProps {
  children: ReactNode;
}

const LOADING_DURATION = 2800;

export function AppShell({
  children,
}: AppShellProps) {
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      setIsLoading(false);
    }, LOADING_DURATION);

    return () => {
      window.clearTimeout(timeout);
    };
  }, []);

  if (isLoading) {
    return (
      <LoadingScreen duration={LOADING_DURATION} />
    );
  }

  return (
    <div className={classes.root}>
      <Header />

      <main className={classes.main}>
        {children}
      </main>

      <Footer />
    </div>
  );
}
