import { Link } from 'react-router-dom';

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="app">
      <header className="header">
        <Link to="/" className="logo">
          Fact-Checker 2026
        </Link>
        <nav>
          <Link to="/candidates">Candidats</Link>
          <Link to="/ingestion">Ingestion</Link>
        </nav>
      </header>
      <main className="main">{children}</main>
    </div>
  );
}

export function SourceLink({ url, label }: { url: string; label?: string }) {
  return (
    <a href={url} target="_blank" rel="noopener noreferrer" className="source-link">
      {label || 'Source'}
    </a>
  );
}

export function formatDate(date: string | null) {
  if (!date) return '—';
  return new Date(date).toLocaleDateString('fr-FR', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export function Loading() {
  return <p className="loading">Chargement…</p>;
}

export function ErrorMessage({ message }: { message: string }) {
  return <p className="error">{message}</p>;
}
