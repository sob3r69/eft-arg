import { NAVIGATION } from './constants';
import classes from './Footer.module.css';

interface FooterProps {
  onUnavailableClick: () => void;
}

export function Footer({ onUnavailableClick }: FooterProps) {
  return (
    <footer className={classes.footer}>
      <nav className={classes.navigation}>
        {NAVIGATION.map(item => (
          <button
            key={item.label}
            type="button"
            className={classes.item}
            onClick={onUnavailableClick}
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
