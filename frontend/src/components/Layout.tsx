import { Link } from 'react-router-dom';
import { VoteStats, formatLoyalty } from '../api/client';

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="app">
      <div className="top-banner" role="status">
        <p>
          Projet open source en construction — exploration de sources publiques
          (YouTube, votes Assemblée, presse). Les données sont collectées
          automatiquement et ne remplacent pas un fact-checking humain.
        </p>
      </div>
      <header className="header">
        <Link to="/" className="logo">
          Fact-Checker 2026
        </Link>
        <nav>
          <Link to="/candidates">Candidats</Link>
          <Link to="/manage">Gestion</Link>
          <Link to="/groups">Groupes</Link>
          <Link to="/parties">Partis</Link>
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

export function GroupBadge({
  name,
  color,
  to,
}: {
  name: string;
  color?: string | null;
  to?: string;
}) {
  const style = color ? { background: color, color: '#fff' } : undefined;
  const content = (
    <span className="group-badge" style={style}>
      {name}
    </span>
  );
  return to ? (
    <Link to={to} className="group-badge-link">
      {content}
    </Link>
  ) : (
    content
  );
}

export function VoteStatsPanel({ stats, title }: { stats: VoteStats | null; title?: string }) {
  if (!stats || stats.total === 0) {
    return (
      <div className="vote-stats empty">
        {title && <h3>{title}</h3>}
        <p>Aucun vote collecté</p>
      </div>
    );
  }

  const max = Math.max(stats.pour, stats.contre, stats.abstention, 1);

  return (
    <div className="vote-stats">
      {title && <h3>{title}</h3>}
      <div className="vote-bars">
        <VoteBar label="Pour" value={stats.pour} max={max} tone="pour" />
        <VoteBar label="Contre" value={stats.contre} max={max} tone="contre" />
        <VoteBar label="Abstention" value={stats.abstention} max={max} tone="abstention" />
      </div>
      <div className="loyalty-row">
        <span>Loyauté au groupe</span>
        <strong>{formatLoyalty(stats.loyalty_rate)}</strong>
        <span className="muted">
          ({stats.aligned_with_group}/{stats.with_group_position} votes comparables)
        </span>
      </div>
    </div>
  );
}

function VoteBar({
  label,
  value,
  max,
  tone,
}: {
  label: string;
  value: number;
  max: number;
  tone: string;
}) {
  const width = `${Math.max((value / max) * 100, value > 0 ? 4 : 0)}%`;
  return (
    <div className="vote-bar-row">
      <span className="vote-bar-label">{label}</span>
      <div className="vote-bar-track">
        <div className={`vote-bar-fill vote-bar-${tone}`} style={{ width }} />
      </div>
      <span className="vote-bar-value">{value}</span>
    </div>
  );
}
