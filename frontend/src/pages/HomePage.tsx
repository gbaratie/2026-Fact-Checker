import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, AppStats } from '../api/client';
import { ErrorMessage, Loading } from '../components/Layout';

export function HomePage() {
  const [stats, setStats] = useState<AppStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .stats()
      .then(setStats)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <ErrorMessage message={error} />;
  if (!stats) return <Loading />;

  return (
    <div>
      <h1>Fact-Checker Présidentielle 2026</h1>
      <p className="subtitle">
        Collecte et exploration des interviews YouTube, votes parlementaires et articles de presse.
      </p>

      <div className="stats-grid">
        <div className="stat-card">
          <span className="stat-value">{stats.candidate_count}</span>
          <span className="stat-label">Candidats suivis</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{stats.database}</span>
          <span className="stat-label">Base de données</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">
            {stats.last_ingestion_at
              ? new Date(stats.last_ingestion_at).toLocaleDateString('fr-FR')
              : '—'}
          </span>
          <span className="stat-label">Dernière ingestion</span>
        </div>
      </div>

      <div className="actions">
        <Link to="/candidates" className="btn">
          Voir les candidats
        </Link>
        <Link to="/manage" className="btn btn-secondary">
          Gestion
        </Link>
        <Link to="/groups" className="btn btn-secondary">
          Groupes
        </Link>
        <Link to="/parties" className="btn btn-secondary">
          Partis
        </Link>
        <Link to="/ingestion" className="btn btn-secondary">
          Historique d&apos;ingestion
        </Link>
      </div>
    </div>
  );
}
