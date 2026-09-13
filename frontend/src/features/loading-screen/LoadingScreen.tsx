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
    <div className={classes.root}>
      <div className={classes.noise} />

      <section className={classes.content}>
        <div className={classes.logo}>
          ESCAPE
          <span>PROTOCOL</span>
        </div>

        <p className={classes.subtitle}>
          LOCAL SECURE TERMINAL
        </p>

        <div className={classes.status}>
          <span className={classes.statusDot} />

          {LOADING_MESSAGES[messageIndex]}
          <span className={classes.blink}>_</span>
        </div>

        <div className={classes.progress}>
          <div
            className={classes.progressBar}
            style={{
              width: `${progress}%`,
            }}
          />
        </div>

        <div className={classes.progressInfo}>
          <span>LOADING</span>

          <span>
            {progress.toString().padStart(3, '0')}
            %
          </span>
        </div>

        <p className={classes.version}>
          BUILD 0.14.9 // SECURE CONNECTION
        </p>
      </section>
    </div>
  );
}
