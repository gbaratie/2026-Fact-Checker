import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { ErrorMessage, Loading } from '../components/Layout';

export function HomePage() {
  const [health, setHealth] = useState<{ status: string; database: string } | null>(null);
  const [candidateCount, setCandidateCount] = useState(0);
  const [lastRun, setLastRun] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.health(), api.candidates(), api.ingestionRuns()])
      .then(([h, candidates, runs]) => {
        setHealth(h);
        setCandidateCount(candidates.length);
        if (runs.length > 0) {
          setLastRun(runs[0].started_at);
        }
      })
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <ErrorMessage message={error} />;
  if (!health) return <Loading />;

  return (
    <div>
      <h1>Fact-Checker Présidentielle 2026</h1>
      <p className="subtitle">
        Collecte et exploration des interviews YouTube, votes parlementaires et articles de presse.
      </p>

      <div className="stats-grid">
        <div className="stat-card">
          <span className="stat-value">{candidateCount}</span>
          <span className="stat-label">Candidats suivis</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{health.database}</span>
          <span className="stat-label">Base de données</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{lastRun ? new Date(lastRun).toLocaleDateString('fr-FR') : '—'}</span>
          <span className="stat-label">Dernière ingestion</span>
        </div>
      </div>

      <div className="actions">
        <Link to="/candidates" className="btn">
          Voir les candidats
        </Link>
        <Link to="/ingestion" className="btn btn-secondary">
          Historique d'ingestion
        </Link>
      </div>
    </div>
  );
}
