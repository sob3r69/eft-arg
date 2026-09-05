import classes from './Footer.module.css';

const navigation = [
  {
    icon:  '☰',
    label: 'ГЛАВНОЕ МЕНЮ',
  },
  {
    icon:  '⬡',
    label: 'УБЕЖИЩЕ',
  },
  {
    icon:  '♟',
    label: 'ПЕРСОНАЖ',
  },
  {
    icon:  '🛒',
    label: 'ТОРГОВЦЫ',
  },
  {
    icon:  '↔',
    label: 'БАРАХОЛКА',
  },
  {
    icon:  '♻',
    label: 'СБОРКИ',
  },
  {
    icon:  '▣',
    label: 'СПРАВОЧНИК',
  },
  {
    icon:  '▤',
    label: 'СООБЩЕНИЯ',
  },
  {
    icon:  '⚙',
    label: 'НАСТРОЙКИ',
  },
];

export function Footer() {
  return (
    <footer className={classes.footer}>
      <nav className={classes.navigation}>
        {navigation.map(item => (
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
