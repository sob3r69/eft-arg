import { useEffect, useState } from 'react';

import { LOADING_MESSAGES } from './constants';
import classes from './LoadingScreen.module.css';

interface LoadingScreenProps {
  duration: number;
}

export function LoadingScreen({
  duration,
}: LoadingScreenProps) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const startedAt = Date.now();

    const interval = window.setInterval(() => {
      const elapsed = Date.now() - startedAt;

      const nextProgress = Math.min(
        Math.round((elapsed / duration) * 100),
        100,
      );

      setProgress(nextProgress);
    }, 30);

    return () => {
      window.clearInterval(interval);
    };
  }, [duration]);

  const messageIndex = Math.min(
    Math.floor((progress / 100) * LOADING_MESSAGES.length),
    LOADING_MESSAGES.length - 1,
  );

  return (
    <div className={classes.root} aria-label="Загрузка рейда" aria-busy="true">
      <div className={classes.background} aria-hidden="true" />
      <div className={classes.vignette} aria-hidden="true" />

      <section className={classes.content}>
        <img
          className={classes.logo}
          src="/images/loading/holostyak-logo.png"
          alt="Escape From Holostyak"
          width={1642}
          height={958}
          fetchPriority="high"
        />

        <div className={classes.loading}>
          <p className={classes.subtitle}>Подготовка к рейду</p>

          <div className={classes.status} role="status" aria-live="polite">
            <span>{LOADING_MESSAGES[messageIndex]}</span>
            <span className={classes.percentage}>
              {progress}
              %
            </span>
          </div>

          <div
            className={classes.progress}
            role="progressbar"
            aria-label="Подготовка к рейду"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={progress}
          >
            <div
              className={classes.progressBar}
              style={{
                width: `${progress}%`,
              }}
            />
          </div>
        </div>
      </section>
    </div>
  );
}
