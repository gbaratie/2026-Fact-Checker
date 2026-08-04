import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, Candidate } from '../api/client';
import { ErrorMessage, GroupBadge, Loading } from '../components/Layout';

const STATUS_LABELS: Record<string, string> = {
  potential: 'Potentiel',
  declared: 'Déclaré',
  withdrawn: 'Retiré',
};

export function CandidatesPage() {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

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
      <p className="subtitle">
        Clique sur une ligne pour ouvrir la fiche — votes, interventions, programme et presse.
      </p>
      {candidates.length === 0 ? (
        <p className="empty-state">
          Aucun candidat en base. Va dans <Link to="/manage">Gestion</Link> pour en ajouter.
        </p>
      ) : (
        <div className="candidate-list">
          {candidates.map((c) => (
            <button
              key={c.id}
              type="button"
              className="candidate-row"
              onClick={() => navigate(`/candidates/${c.slug}`)}
            >
              <div className="candidate-row-main">
                <span className="candidate-row-name">{c.full_name}</span>
                <span className={`badge badge-${c.status}`}>
                  {STATUS_LABELS[c.status] || c.status}
                </span>
              </div>
              <div className="candidate-row-meta">
                <span className="candidate-row-party">{c.party || 'Parti non renseigné'}</span>
                {c.parliamentary_group ? (
                  <GroupBadge
                    name={c.parliamentary_group.name}
                    color={c.parliamentary_group.color}
                  />
                ) : (
                  <span className="muted">Pas de groupe AN</span>
                )}
              </div>
              <span className="candidate-row-chevron" aria-hidden>
                →
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
