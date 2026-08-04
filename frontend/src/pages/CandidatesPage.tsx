import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, Candidate } from '../api/client';
import { ErrorMessage, GroupBadge, Loading } from '../components/Layout';

export function CandidatesPage() {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .candidates()
      .then(setCandidates)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (error) return <ErrorMessage message={error} />;
  if (loading) return <Loading />;

  return (
    <div>
      <h1>Candidats</h1>
      <p className="subtitle">Vue individuelle — votes, parti et groupe parlementaire.</p>
      {candidates.length === 0 ? (
        <p className="empty-state">
          Aucun candidat en base. Va dans <Link to="/manage">Gestion</Link> pour importer le
          seed ou en ajouter.
        </p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Nom</th>
              <th>Parti</th>
              <th>Groupe AN</th>
              <th>Statut</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {candidates.map((c) => (
              <tr key={c.id}>
                <td>{c.full_name}</td>
                <td>
                  {c.party ? (
                    <Link to={`/parties/${encodeURIComponent(c.party)}`}>{c.party}</Link>
                  ) : (
                    '—'
                  )}
                </td>
                <td>
                  {c.parliamentary_group ? (
                    <GroupBadge
                      name={c.parliamentary_group.name}
                      color={c.parliamentary_group.color}
                      to={`/groups/${c.parliamentary_group.slug}`}
                    />
                  ) : (
                    '—'
                  )}
                </td>
                <td>
                  <span className={`badge badge-${c.status}`}>{c.status}</span>
                </td>
                <td>
                  <Link to={`/candidates/${c.slug}`}>Détail</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
