import type { Trader } from '#/shared/api/game';
import { useQuery } from '@tanstack/react-query';

import { Link } from '@tanstack/react-router';
import { useEffect } from 'react';
import { useTraderSelection } from '#/providers/TraderSelectionProvider';
import { getTraders } from '#/shared/api/game';

import classes from './Header.module.css';

export function Header() {
  const { selectedTraderSlug, setSelectedTraderSlug } = useTraderSelection();

  const tradersQuery = useQuery({
    queryKey: ['traders'],
    queryFn:  getTraders,
  });

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
          >
            <span className={classes.navigationIcon}>
              ♜
            </span>

            ТОРГОВЛЯ
          </button>

          <Link
            to="/"
            className={`${classes.navigationItem} ${classes.navigationItemActive}`}
          >
            <span className={classes.navigationIcon}>
              ✓
            </span>

            ЗАДАНИЯ
          </Link>

          <button
            type="button"
            className={classes.navigationItem}
          >
            <span className={classes.navigationIcon}>
              ◈
            </span>

            УСЛУГИ
          </button>
        </nav>

        <button
          type="button"
          className={classes.visitButton}
        >
          <span>☏</span>
          ПОСЕТИТЬ
        </button>

        <button
          type="button"
          className={classes.backButton}
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
              </div>

              <div className={classes.traderName}>
                {trader.name}
              </div>

              <div className={classes.traderStats}>
                <span>♟ 3.75</span>
                <span>◴ 00:31:54</span>
              </div>

              <span className={classes.traderStatus}>
                ✓
              </span>
            </button>
          ))}
        </div>

        <div className={classes.profile}>
          <div className={classes.profileInfo}>
            <strong className={classes.profileName}>
              groom_01
            </strong>

            <div className={classes.profileMoney}>
              <span>₽ 7 657 179</span>
              <span>€ 7 379</span>
              <span>$ 11 928</span>
            </div>

            <div className={classes.profileDivider} />

            <div className={classes.profileStats}>
              <span>
                Текущее отношение:
                <strong> III</strong>
              </span>

              <span>
                LVL 29
              </span>

              <span>
                3.75
              </span>
            </div>
          </div>

          <div className={classes.profileLevel}>
            29
          </div>

          <div className={classes.profileAvatar}>
            <span>
              ?
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}

interface TraderCard {
  id:         string;
  name:       string;
  image:      string;
  levelLabel: string;
  disabled:   boolean;
}

function getTraderCards(traders: Trader[] | undefined, isLoading: boolean, isError: boolean): TraderCard[] {
  if (traders?.length) {
    return traders.map((trader, index) => ({
      id:         trader.slug,
      name:       trader.name,
      image:      trader.image ?? '',
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
