const VIEWS = [
  { value: 'comparison', label: 'Comparación' },
  { value: 'history', label: 'Histórico' },
];

// Navbar tipo cápsula: logo a la izquierda, enlaces de las vistas al centro y estado en vivo a la derecha
export default function Navbar({ view, onViewChange }) {
  return (
    <nav className="navbar" aria-label="Navegación principal">
      <div className="navbar__brand">
        <span className="navbar__logo">
          <img src="/icons/termometro.svg" alt="" />
        </span>
        <span className="navbar__title">Weather Dashboard</span>
      </div>

      <ul className="navbar__links">
        {VIEWS.map(({ value, label }) => {
          const isActive = view === value;
          return (
            <li key={value}>
              <button
                type="button"
                className={isActive ? 'navbar__link is-active' : 'navbar__link'}
                aria-current={isActive ? 'page' : undefined}
                onClick={() => onViewChange(value)}
              >
                {label}
              </button>
            </li>
          );
        })}
      </ul>

      <span className="live-pill">
        <span className="live-dot" />
        <span className="live-pill__text">En vivo</span>
      </span>
    </nav>
  );
}
