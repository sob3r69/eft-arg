import { createFileRoute } from '@tanstack/react-router';

import classes from './index.module.css';

export const Route = createFileRoute('/')({
  component: HomePage,
});

function HomePage() {
  return (
    <div className={classes.root}>
      <section className={classes.hero}>
        <p className={classes.eyebrow}>
        </p>

        <h1>
          ДОБРО ПОЖАЛОВАТЬ,
          <br />
          <span>ОПЕРАТИВНИК.</span>
        </h1>

        <p className={classes.description}>
          Терминал активирован. Ваш профиль обнаружен
          в локальной сети. Дальнейшие инструкции
          будут передаваться через защищённый канал.
        </p>
      </section>

      <section className={classes.grid}>
        <article className={classes.primaryCard}>
          <header>
            <span>ТЕКУЩЕЕ ЗАДАНИЕ</span>

            <span className={classes.status}>
              АКТИВНО
            </span>
          </header>

          <div className={classes.questNumber}>
            ЗАДАНИЕ 01
          </div>

          <h2>
            ТОЧКА ВХОДА
          </h2>

          <p>
            Получите первое сообщение и следуйте
            предоставленным инструкциям.
          </p>

          <button type="button">
            ОТКРЫТЬ ЗАДАНИЕ
          </button>
        </article>

        <aside className={classes.stats}>
          <article className={classes.statCard}>
            <span>ПРОГРЕСС ОПЕРАЦИИ</span>

            <strong>
              01 / 08
            </strong>

            <div className={classes.statProgress}>
              <div style={{ width: '12.5%' }} />
            </div>
          </article>

          <article className={classes.statCard}>
            <span>СТАТУС</span>

            <strong className={classes.online}>
              ● ONLINE
            </strong>
          </article>

          <article className={classes.statCard}>
            <span>ПОЛУЧЕНО ПРЕДМЕТОВ</span>

            <strong>
              00
            </strong>
          </article>
        </aside>
      </section>
    </div>
  );
}
