import type { Trader } from '#/shared/api/game';
import { useQuery } from '@tanstack/react-query';

import { Link } from '@tanstack/react-router';
import { ChartNoAxesColumnIncreasing, CircleCheck, Crown, Handshake, Headset, ShoppingCart, TimerReset } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useTraderSelection } from '#/providers/TraderSelectionProvider';
import { getPlayerProfile, getTraders } from '#/shared/api/game';

import classes from './Header.module.css';

interface HeaderProps {
  onUnavailableClick: () => void;
}

export function Header({ onUnavailableClick }: HeaderProps) {
  const { selectedTraderSlug, setSelectedTraderSlug } = useTraderSelection();

  const tradersQuery = useQuery({
    queryKey:        ['traders'],
    queryFn:         getTraders,
    refetchInterval: 5000,
  });

  const profileQuery = useQuery({
    queryKey:        ['player'],
    queryFn:         getPlayerProfile,
    refetchInterval: 5000,
  });
  const profile = profileQuery.data;
  const selectedTrader = tradersQuery.data?.find(trader => trader.slug === selectedTraderSlug);
  const formatMoney = (value: number | undefined) => value === undefined ? '—' : value.toLocaleString('ru-RU');

  const traders = getTraderCards(tradersQuery.data, tradersQuery.isLoading, tradersQuery.isError);

  useEffect(() => {
    const firstTrader = tradersQuery.data?.[0];

    if (!selectedTraderSlug && firstTrader) {
      setSelectedTraderSlug(firstTrader.slug);
    }
  }, [selectedTraderSlug, setSelectedTraderSlug, tradersQuery.data]);

  return (
    <header className={classes.header}>
      <div className={classes.topRow}>
        <nav className={classes.mainNavigation}>
          <button
            type="button"
            className={classes.navigationItem}
            onClick={onUnavailableClick}
          >
            <span className={classes.navigationIcon}>
              <ShoppingCart aria-hidden="true" />
            </span>

            ТОРГОВЛЯ
          </button>

          <Link
            to="/"
            className={`${classes.navigationItem} ${classes.navigationItemActive}`}
          >
            <span className={classes.navigationIcon}>
              <CircleCheck aria-hidden="true" />
            </span>

            ЗАДАНИЯ
          </Link>

          <button
            type="button"
            className={classes.navigationItem}
            onClick={onUnavailableClick}
          >
            <span className={classes.navigationIcon}>
              <Handshake aria-hidden="true" />
            </span>

            УСЛУГИ
          </button>
        </nav>

        <button
          type="button"
          className={classes.visitButton}
          onClick={onUnavailableClick}
        >
          <Headset aria-hidden="true" />
          ПОСЕТИТЬ
        </button>

        <button
          type="button"
          className={classes.backButton}
          onClick={onUnavailableClick}
        >
          НАЗАД
        </button>
      </div>

      <div className={classes.bottomRow}>
        <div className={classes.traders}>
          {traders.map(trader => (
            <button
              key={trader.id}
              type="button"
              className={`${classes.trader} ${trader.id === selectedTraderSlug ? classes.traderActive : ''}`}
              disabled={trader.disabled}
              aria-pressed={trader.id === selectedTraderSlug}
              onClick={() => {
                setSelectedTraderSlug(trader.id);
              }}
            >
              <span className={classes.traderLevel}>
                {trader.levelLabel}
              </span>

              <div className={classes.traderAvatar}>
                <span>
                  ?
                </span>

                {trader.image && (
                  <img
                    key={trader.image}
                    alt=""
                    src={trader.image}
                    onError={(event) => {
                      event.currentTarget.hidden = true;
                    }}
                  />
                )}
                <span className={classes.traderQuestion} aria-hidden="true">?</span>
              </div>

              <div className={classes.traderName}>
                {trader.name}
              </div>

              <div className={classes.traderStats}>
                <span>
                  <ChartNoAxesColumnIncreasing aria-hidden="true" />
                  {/* TRADER REPUTATION */}
                  {trader.reputation ?? '—'}
                </span>
                <span>
                  <TimerReset aria-hidden="true" />
                  {/* TRADER FAKE TIMER */}
                  {trader.reputation === undefined ? '—' : <TraderCountdown />}
                </span>
              </div>

              <span className={classes.traderStatus}>
                <CircleCheck aria-hidden="true" />
              </span>
            </button>
          ))}
        </div>

        <div className={classes.profile}>
          <div className={classes.profileInfo}>
            <strong className={classes.profileName}>
              {profile ? `${profile.nickname} (вы)` : profileQuery.isError ? 'Нет связи' : 'Загрузка…'}
            </strong>

            <div className={classes.profileMoney}>
              <span>
                ₽
                {formatMoney(profile?.rubles)}
              </span>
              <span>
                €
                {formatMoney(profile?.euros)}
              </span>
              <span>
                $
                {formatMoney(profile?.dollars)}
              </span>
            </div>

            <div className={classes.profileDivider} />
            <span className={classes.profileEmblem} aria-hidden="true" />

            <div className={classes.profileStats}>
              <span>
                Текущее отношение:
                <strong className={classes.loyaltyLevel}>III</strong>
              </span>

              <span>
                LVL
                {' '}
                {profile?.level ?? '—'}
              </span>

              <span>
                <ChartNoAxesColumnIncreasing aria-hidden="true" />
                {selectedTrader?.reputation ?? '—'}
              </span>
              <span>
                {formatMoney(profile?.experience)}
                {' '}
                EXP
              </span>
            </div>
            <div className={`${classes.profileStats} ${classes.nextLevel}`}>
              <span>
                Следующий УЛ:
                <strong className={classes.loyaltyLevel}><Crown aria-hidden="true" /></strong>
              </span>
              <span>
                LVL
                <b>37</b>
              </span>
              <span>
                <ChartNoAxesColumnIncreasing aria-hidden="true" />
                <b>5.80</b>
              </span>
            </div>
          </div>

          <div className={classes.profileAvatar}>
            {profile?.avatar
              ? (
                  <img
                    key={profile.avatar}
                    src={profile.avatar}
                    alt={`Аватар ${profile.nickname}`}
                    onError={(event) => { event.currentTarget.hidden = true; }}
                  />
                )
              : <span className={classes.avatarPlaceholder} aria-hidden="true">?</span>}
            <span className={classes.profileLevel} aria-label={`Уровень ${profile?.level ?? 'неизвестен'}`}>
              {profile?.level ?? '—'}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}

const MAX_TRADER_TIMER_SECONDS = 90 * 60;

function TraderCountdown() {
  const [seconds, setSeconds] = useState<number | null>(null);

  useEffect(() => {
    const randomDuration = () => (Math.floor(Math.random() * MAX_TRADER_TIMER_SECONDS) + 1) * 1000;
    let deadline = Date.now() + randomDuration();

    const tick = () => {
      const now = Date.now();
      if (now >= deadline) {
        deadline = now + randomDuration();
      }
      setSeconds(Math.ceil((deadline - now) / 1000));
    };

    const initialTick = window.setTimeout(tick, 0);
    const interval = window.setInterval(tick, 1000);
    return () => {
      window.clearTimeout(initialTick);
      window.clearInterval(interval);
    };
  }, []);

  if (seconds === null) {
    return <>—</>;
  }

  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainingSeconds = seconds % 60;

  return <>{[hours, minutes, remainingSeconds].map(value => String(value).padStart(2, '0')).join(':')}</>;
}

interface TraderCard {
  id:          string;
  name:        string;
  image:       string;
  levelLabel:  string;
  disabled:    boolean;
  reputation?: string;
}

function getTraderCards(traders: Trader[] | undefined, isLoading: boolean, isError: boolean): TraderCard[] {
  if (traders?.length) {
    return traders.map((trader, index) => ({
      id:         trader.slug,
      name:       trader.name,
      image:      trader.image ?? '',
      reputation: trader.reputation,
      levelLabel: getLevelLabel(index),
      disabled:   !trader.available,
    }));
  }

  if (isLoading) {
    return Array.from({ length: 6 }, (_, index) => ({
      id:         `loading-${index}`,
      name:       'Загрузка',
      image:      '',
      levelLabel: 'I',
      disabled:   true,
    }));
  }

  return [{
    id:         'traders-unavailable',
    name:       isError ? 'Нет связи' : 'Нет данных',
    image:      '',
    levelLabel: 'I',
    disabled:   true,
  }];
}

function getLevelLabel(index: number) {
  return index === 2 ? 'I' : 'III';
}
