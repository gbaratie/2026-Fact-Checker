import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, Candidate } from '../api/client';
import { ErrorMessage, Loading } from '../components/Layout';

export function CandidatesPage() {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .candidates()
      .then(setCandidates)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <ErrorMessage message={error} />;
  if (candidates.length === 0 && !error) return <Loading />;

  return (
    <div>
      <h1>Candidats</h1>
      <table className="data-table">
        <thead>
          <tr>
            <th>Nom</th>
            <th>Parti</th>
            <th>Statut</th>
            <th>ID parlementaire</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {candidates.map((c) => (
            <tr key={c.id}>
              <td>{c.full_name}</td>
              <td>{c.party || '—'}</td>
              <td>
                <span className={`badge badge-${c.status}`}>{c.status}</span>
              </td>
              <td>{c.external_ids?.depute_id || '—'}</td>
              <td>
                <Link to={`/candidates/${c.slug}`}>Détail</Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
