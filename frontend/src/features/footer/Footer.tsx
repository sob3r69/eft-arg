import { NAVIGATION } from './constants';
import classes from './Footer.module.css';

export function Footer() {
  return (
    <footer className={classes.footer}>
      <nav className={classes.navigation}>
        {NAVIGATION.map(item => (
          <button
            key={item.label}
            type="button"
            className={classes.item}
          >
            <span className={classes.icon}>
              {item.icon}
            </span>

            <span>
              {item.label}
            </span>
          </button>
        ))}
      </nav>
    </footer>
  );
}
