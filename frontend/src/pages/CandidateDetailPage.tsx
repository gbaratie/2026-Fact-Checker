import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  api,
  Article,
  CandidateDetail,
  Interview,
  ParliamentaryVote,
  ProgramDocument,
} from '../api/client';
import {
  ErrorMessage,
  formatDate,
  GroupBadge,
  Loading,
  SourceLink,
  VoteStatsPanel,
} from '../components/Layout';

type Tab = 'votes' | 'interventions' | 'programme' | 'articles';

const KIND_LABELS: Record<string, string> = {
  presidential_program: 'Programme présidentiel',
  party_program: 'Programme de parti',
  campaign_site: 'Site de campagne',
  platform_outline: 'Ébauche de plateforme',
};

export function CandidateDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const [candidate, setCandidate] = useState<CandidateDetail | null>(null);
  const [tab, setTab] = useState<Tab>('votes');
  const [interviews, setInterviews] = useState<Interview[]>([]);
  const [programs, setPrograms] = useState<ProgramDocument[]>([]);
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
    if (tab === 'interventions') {
      api.interviews(slug).then((r) => setInterviews(r.items));
    } else if (tab === 'programme') {
      api.programs(slug).then((r) => setPrograms(r.items));
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
          <span className="stat-label">Interventions</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{candidate.program_count}</span>
          <span className="stat-label">Programmes</span>
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
          className={tab === 'interventions' ? 'active' : ''}
          onClick={() => setTab('interventions')}
        >
          Interventions ({candidate.interview_count})
        </button>
        <button
          className={tab === 'programme' ? 'active' : ''}
          onClick={() => setTab('programme')}
        >
          Programme ({candidate.program_count})
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

      {tab === 'interventions' && (
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
                <td colSpan={5}>Aucune intervention collectée</td>
              </tr>
            )}
          </tbody>
        </table>
      )}

      {tab === 'programme' && (
        <div className="program-list">
          {programs.map((p) => {
            const retrievedVia =
              (p.source.raw_metadata?.retrieved_via as string | undefined) || 'curated_seed';
            const sourceUrl =
              (p.source.raw_metadata?.source_url as string | undefined) || p.url;
            return (
              <article key={p.id} className="program-card">
                <header className="program-card-header">
                  <h2>{p.title}</h2>
                  <p className="program-meta">
                    <span>{KIND_LABELS[p.kind] || p.kind}</span>
                    {p.year != null && <span>{p.year}</span>}
                    {p.publisher && <span>{p.publisher}</span>}
                  </p>
                </header>
                {p.note && <p className="program-note">{p.note}</p>}
                {p.excerpt && <p className="program-excerpt">{p.excerpt.slice(0, 400)}…</p>}
                <footer className="program-card-footer">
                  <SourceLink url={p.url} label="Consulter le document" />
                  <span className="provenance">
                    Récupéré via {retrievedVia} ·{' '}
                    <SourceLink url={sourceUrl} label="provenance" />
                  </span>
                </footer>
              </article>
            );
          })}
          {programs.length === 0 && <p className="empty-state">Aucun document de programme</p>}
        </div>
      )}

      {tab === 'articles' && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Titre</th>
              <th>Éditeur</th>
              <th>Date</th>
              <th>Extrait</th>
              <th>Article</th>
              <th>Récupéré via</th>
            </tr>
          </thead>
          <tbody>
            {articles.map((a) => {
              const feedUrl = a.source.raw_metadata?.feed_url as string | undefined;
              const feedTitle =
                (a.source.raw_metadata?.feed_title as string | undefined) ||
                (a.source.raw_metadata?.publisher as string | undefined) ||
                a.publisher;
              return (
                <tr key={a.id}>
                  <td>{a.title}</td>
                  <td>{a.publisher || '—'}</td>
                  <td>{formatDate(a.published_at)}</td>
                  <td>{a.excerpt ? `${a.excerpt.slice(0, 80)}…` : '—'}</td>
                  <td>
                    <SourceLink url={a.url || a.source.url} label="Lire" />
                  </td>
                  <td>
                    {feedUrl ? (
                      <span className="provenance">
                        RSS · <SourceLink url={feedUrl} label={feedTitle || 'flux'} />
                      </span>
                    ) : (
                      <span className="provenance">—</span>
                    )}
                  </td>
                </tr>
              );
            })}
            {articles.length === 0 && (
              <tr>
                <td colSpan={6}>Aucun article collecté</td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}
