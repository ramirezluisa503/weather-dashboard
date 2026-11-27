const VIEWS = [
  { value: 'comparison', label: 'Comparación' },
  { value: 'history', label: 'Histórico' },
];

const STATUS_LABELS = {
  open: 'En vivo',
  reconnecting: 'Reconectando…',
  connecting: 'Conectando…',
};

// Navbar tipo cápsula: logo a la izquierda, enlaces de las vistas al centro y estado en vivo a la derecha
export default function Navbar({ view, onViewChange, socketStatus }) {
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

      {/* Estado real de la conexión WebSocket */}
      <span className="live-pill" title={STATUS_LABELS[socketStatus]}>
        <span className={`live-dot live-dot--${socketStatus}`} />
        <span className="live-pill__text">{STATUS_LABELS[socketStatus]}</span>
      </span>
    </nav>
  );
}
