import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api, PartyDetail, formatLoyalty } from '../api/client';
import {
  ErrorMessage,
  GroupBadge,
  Loading,
  VoteStatsPanel,
} from '../components/Layout';

export function PartiesPage() {
  const [parties, setParties] = useState<PartyDetail[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .parties()
      .then(setParties)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <ErrorMessage message={error} />;
  if (!parties) return <Loading />;

  return (
    <div>
      <h1>Partis politiques</h1>
      <p className="subtitle">
        Vue agrégée par parti déclaré sur les candidats (RN, LFI, LR…).
      </p>
      <div className="card-grid">
        {parties.map((p) => (
          <Link
            key={p.party}
            to={`/parties/${encodeURIComponent(p.party)}`}
            className="entity-card"
          >
            <h2>{p.party}</h2>
            <p className="muted">
              {p.candidate_count} candidat{p.candidate_count > 1 ? 's' : ''} · {p.vote_count}{' '}
              votes
            </p>
            <p>
              Loyauté groupe : <strong>{formatLoyalty(p.vote_stats?.loyalty_rate)}</strong>
            </p>
          </Link>
        ))}
      </div>
    </div>
  );
}

export function PartyDetailPage() {
  const { party } = useParams<{ party: string }>();
  const [detail, setDetail] = useState<PartyDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!party) return;
    api
      .party(decodeURIComponent(party))
      .then(setDetail)
      .catch((e) => setError(e.message));
  }, [party]);

  if (error) return <ErrorMessage message={error} />;
  if (!detail) return <Loading />;

  return (
    <div>
      <Link to="/parties" className="back-link">
        ← Partis
      </Link>
      <h1>{detail.party}</h1>
      <p className="subtitle">
        {detail.candidate_count} candidat{detail.candidate_count > 1 ? 's' : ''} suivis
      </p>

      <VoteStatsPanel stats={detail.vote_stats} title="Profil de vote agrégé" />

      <h2 className="section-title">Candidats</h2>
      <table className="data-table">
        <thead>
          <tr>
            <th>Nom</th>
            <th>Groupe AN</th>
            <th>Statut</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {detail.candidates.map((c) => (
            <tr key={c.id}>
              <td>{c.full_name}</td>
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
    </div>
  );
}
