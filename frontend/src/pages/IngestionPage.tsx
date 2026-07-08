import { useEffect, useState } from 'react';
import { api, IngestionRun } from '../api/client';
import { ErrorMessage, formatDate, Loading } from '../components/Layout';

export function IngestionPage() {
  const [runs, setRuns] = useState<IngestionRun[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .ingestionRuns()
      .then(setRuns)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <ErrorMessage message={error} />;
  if (runs.length === 0 && !error) return <Loading />;

  return (
    <div>
      <h1>Historique d'ingestion</h1>
      <table className="data-table">
        <thead>
          <tr>
            <th>Début</th>
            <th>Fin</th>
            <th>Statut</th>
            <th>Interviews</th>
            <th>Votes</th>
            <th>Articles</th>
            <th>Erreurs</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.id}>
              <td>{formatDate(run.started_at)}</td>
              <td>{formatDate(run.finished_at)}</td>
              <td>
                <span className={`badge badge-${run.status}`}>{run.status}</span>
              </td>
              <td>{run.stats?.interviews ?? 0}</td>
              <td>{run.stats?.votes ?? 0}</td>
              <td>{run.stats?.articles ?? 0}</td>
              <td>
                {run.errors?.length > 0 ? (
                  <details>
                    <summary>{run.errors.length} erreur(s)</summary>
                    <ul>
                      {run.errors.map((e, i) => (
                        <li key={i}>{e}</li>
                      ))}
                    </ul>
                  </details>
                ) : (
                  '—'
                )}
              </td>
            </tr>
          ))}
          {runs.length === 0 && (
            <tr>
              <td colSpan={7}>Aucune ingestion effectuée</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
