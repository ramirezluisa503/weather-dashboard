export default function Header() {
  return (
    <header className="header glass">
      <div>
        <h1>Weather Dashboard</h1>
        <p className="subtitle">
          Compara el clima de dos ciudades en tiempo real
        </p>
      </div>
      <span className="live-badge">
        <span className="live-dot" /> En vivo
      </span>
    </header>
  );
}
