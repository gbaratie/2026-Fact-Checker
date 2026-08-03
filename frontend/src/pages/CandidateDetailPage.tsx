import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  api,
  Article,
  CandidateDetail,
  Interview,
  ParliamentaryVote,
} from '../api/client';
import {
  ErrorMessage,
  formatDate,
  GroupBadge,
  Loading,
  SourceLink,
  VoteStatsPanel,
} from '../components/Layout';

type Tab = 'votes' | 'interviews' | 'articles';

export function CandidateDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const [candidate, setCandidate] = useState<CandidateDetail | null>(null);
  const [tab, setTab] = useState<Tab>('votes');
  const [interviews, setInterviews] = useState<Interview[]>([]);
  const [votes, setVotes] = useState<ParliamentaryVote[]>([]);
  const [articles, setArticles] = useState<Article[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!slug) return;
    api
      .candidate(slug)
      .then(setCandidate)
      .catch((e) => setError(e.message));
  }, [slug]);

  useEffect(() => {
    if (!slug) return;
    if (tab === 'interviews') {
      api.interviews(slug).then((r) => setInterviews(r.items));
    } else if (tab === 'votes') {
      api.votes(slug).then((r) => setVotes(r.items));
    } else {
      api.articles(slug).then((r) => setArticles(r.items));
    }
  }, [slug, tab]);

  if (error) return <ErrorMessage message={error} />;
  if (!candidate) return <Loading />;

  const group = candidate.parliamentary_group;

  return (
    <div>
      <Link to="/candidates" className="back-link">
        ← Retour
      </Link>
      <h1>{candidate.full_name}</h1>
      <p className="meta">
        {candidate.party && (
          <Link to={`/parties/${encodeURIComponent(candidate.party)}`} className="meta-link">
            Parti : {candidate.party}
          </Link>
        )}
        {group && (
          <GroupBadge name={group.name} color={group.color} to={`/groups/${group.slug}`} />
        )}
        <span className={`badge badge-${candidate.status}`}>{candidate.status}</span>
      </p>
      {group && <p className="group-fullname">{group.full_name}</p>}

      <div className="stats-grid">
        <div className="stat-card">
          <span className="stat-value">{candidate.vote_count}</span>
          <span className="stat-label">Votes</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{candidate.interview_count}</span>
          <span className="stat-label">Interviews</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{candidate.article_count}</span>
          <span className="stat-label">Articles</span>
        </div>
      </div>

      <VoteStatsPanel stats={candidate.vote_stats} title="Profil de vote" />

      <div className="tabs">
        <button className={tab === 'votes' ? 'active' : ''} onClick={() => setTab('votes')}>
          Votes ({candidate.vote_count})
        </button>
        <button
          className={tab === 'interviews' ? 'active' : ''}
          onClick={() => setTab('interviews')}
        >
          Interviews ({candidate.interview_count})
        </button>
        <button className={tab === 'articles' ? 'active' : ''} onClick={() => setTab('articles')}>
          Articles ({candidate.article_count})
        </button>
      </div>

      {tab === 'votes' && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Scrutin</th>
              <th>Position</th>
              <th>Groupe</th>
              <th>Aligné</th>
              <th>Date</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            {votes.map((v) => (
              <tr key={v.id}>
                <td>{v.title}</td>
                <td>
                  <span className={`vote-${v.position}`}>{v.position}</span>
                </td>
                <td>
                  {v.group_position ? (
                    <span className={`vote-${v.group_position}`}>{v.group_position}</span>
                  ) : (
                    '—'
                  )}
                </td>
                <td>
                  {v.aligned_with_group == null ? (
                    '—'
                  ) : v.aligned_with_group ? (
                    <span className="align-yes">oui</span>
                  ) : (
                    <span className="align-no">non</span>
                  )}
                </td>
                <td>{formatDate(v.vote_date)}</td>
                <td>
                  <SourceLink url={v.source.url} />
                </td>
              </tr>
            ))}
            {votes.length === 0 && (
              <tr>
                <td colSpan={6}>Aucun vote collecté</td>
              </tr>
            )}
          </tbody>
        </table>
      )}

      {tab === 'interviews' && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Titre</th>
              <th>Chaîne</th>
              <th>Date</th>
              <th>Transcript</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            {interviews.map((i) => (
              <tr key={i.id}>
                <td>{i.title}</td>
                <td>{i.channel_name || '—'}</td>
                <td>{formatDate(i.published_at)}</td>
                <td>{i.transcript ? `${i.transcript.slice(0, 80)}…` : '—'}</td>
                <td>
                  <SourceLink url={i.source.url} label="YouTube" />
                </td>
              </tr>
            ))}
            {interviews.length === 0 && (
              <tr>
                <td colSpan={5}>Aucune interview collectée</td>
              </tr>
            )}
          </tbody>
        </table>
      )}

      {tab === 'articles' && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Titre</th>
              <th>Éditeur</th>
              <th>Date</th>
              <th>Extrait</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            {articles.map((a) => (
              <tr key={a.id}>
                <td>{a.title}</td>
                <td>{a.publisher || '—'}</td>
                <td>{formatDate(a.published_at)}</td>
                <td>{a.excerpt ? `${a.excerpt.slice(0, 80)}…` : '—'}</td>
                <td>
                  <SourceLink url={a.source.url} label="Article" />
                </td>
              </tr>
            ))}
            {articles.length === 0 && (
              <tr>
                <td colSpan={5}>Aucun article collecté</td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}
