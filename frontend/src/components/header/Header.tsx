import { Link } from '@tanstack/react-router';

import classes from './Header.module.css';

const traders = [
  {
    id:    'prapor',
    name:  'Прапор',
    level: 'III',
  },
  {
    id:    'therapist',
    name:  'Терапевт',
    level: 'III',
  },
  {
    id:    'skier',
    name:  'Скупщик',
    level: 'I',
  },
  {
    id:    'skier-2',
    name:  'Лыжник',
    level: 'III',
  },
  {
    id:    'peacekeeper',
    name:  'Миротворец',
    level: 'III',
  },
  {
    id:    'mechanic',
    name:  'Механик',
    level: 'III',
  },
];

export function Header() {
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
              className={classes.trader}
            >
              <span className={classes.traderLevel}>
                {trader.level}
              </span>

              <div className={classes.traderAvatar}>
                <span>
                  ?
                </span>
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
