import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api, GroupDetail, formatLoyalty } from '../api/client';
import {
  ErrorMessage,
  GroupBadge,
  Loading,
  VoteStatsPanel,
} from '../components/Layout';

export function GroupsPage() {
  const [groups, setGroups] = useState<GroupDetail[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .groups()
      .then(setGroups)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <ErrorMessage message={error} />;
  if (!groups) return <Loading />;

  return (
    <div>
      <h1>Groupes parlementaires</h1>
      <p className="subtitle">
        Agrégation des votes des candidats suivis, par groupe à l&apos;Assemblée.
      </p>
      <div className="card-grid">
        {groups.map((g) => (
          <Link key={g.id} to={`/groups/${g.slug}`} className="entity-card">
            <div className="entity-card-head">
              <GroupBadge name={g.name} color={g.color} />
              {g.spectrum && <span className="muted">{g.spectrum}</span>}
            </div>
            <h2>{g.full_name}</h2>
            <p className="muted">
              {g.member_count} candidat{g.member_count > 1 ? 's' : ''} · {g.vote_count} votes
            </p>
            <p>
              Loyauté moyenne : <strong>{formatLoyalty(g.vote_stats?.loyalty_rate)}</strong>
            </p>
          </Link>
        ))}
      </div>
      {groups.length === 0 && <p>Aucun groupe lié pour l&apos;instant.</p>}
    </div>
  );
}

export function GroupDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const [group, setGroup] = useState<GroupDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!slug) return;
    api
      .group(slug)
      .then(setGroup)
      .catch((e) => setError(e.message));
  }, [slug]);

  if (error) return <ErrorMessage message={error} />;
  if (!group) return <Loading />;

  return (
    <div>
      <Link to="/groups" className="back-link">
        ← Groupes
      </Link>
      <div className="entity-card-head">
        <GroupBadge name={group.name} color={group.color} />
        {group.spectrum && <span className="muted">{group.spectrum}</span>}
      </div>
      <h1>{group.full_name}</h1>
      <p className="subtitle">
        Chambre : {group.chamber}
        {group.legislature ? ` · législature ${group.legislature}` : ''}
      </p>

      <VoteStatsPanel stats={group.vote_stats} title="Votes du groupe (candidats suivis)" />

      <h2 className="section-title">Membres suivis</h2>
      <table className="data-table">
        <thead>
          <tr>
            <th>Candidat</th>
            <th>Parti</th>
            <th>Votes</th>
            <th>Loyauté</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {group.members.map((m) => (
            <tr key={m.id}>
              <td>{m.full_name}</td>
              <td>
                {m.party ? (
                  <Link to={`/parties/${encodeURIComponent(m.party)}`}>{m.party}</Link>
                ) : (
                  '—'
                )}
              </td>
              <td>{m.vote_count}</td>
              <td>{formatLoyalty(m.vote_stats?.loyalty_rate)}</td>
              <td>
                <Link to={`/candidates/${m.slug}`}>Détail</Link>
              </td>
            </tr>
          ))}
          {group.members.length === 0 && (
            <tr>
              <td colSpan={5}>Aucun candidat suivi dans ce groupe</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
