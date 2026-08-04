import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  api,
  Article,
  CandidateDetail,
  CHAMBER_LABELS,
  clairScrutinUrl,
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
type ChamberFilter = 'all' | 'assemblee' | 'senat' | 'parlement_europeen';

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
  const [chamber, setChamber] = useState<ChamberFilter>('all');
  const [interviews, setInterviews] = useState<Interview[] | null>(null);
  const [programs, setPrograms] = useState<ProgramDocument[] | null>(null);
  const [votes, setVotes] = useState<ParliamentaryVote[] | null>(null);
  const [articles, setArticles] = useState<Article[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tabLoading, setTabLoading] = useState(false);

  useEffect(() => {
    if (!slug) return;
    setCandidate(null);
    setInterviews(null);
    setPrograms(null);
    setVotes(null);
    setArticles(null);
    setError(null);
    setTab('votes');
    setChamber('all');

    let cancelled = false;
    Promise.all([api.candidate(slug), api.votes(slug)])
      .then(([detail, votePage]) => {
        if (cancelled) return;
        setCandidate(detail);
        setVotes(votePage.items);
      })
      .catch((e) => {
        if (!cancelled) setError(e.message);
      });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  useEffect(() => {
    if (!slug || !candidate) return;
    if (tab === 'votes') return; // préchargé avec le détail candidat

    let cancelled = false;

    async function loadTab() {
      if (tab === 'interventions' && interviews !== null) return;
      if (tab === 'programme' && programs !== null) return;
      if (tab === 'articles' && articles !== null) return;

      setTabLoading(true);
      try {
        if (tab === 'interventions') {
          const r = await api.interviews(slug!);
          if (!cancelled) setInterviews(r.items);
        } else if (tab === 'programme') {
          const r = await api.programs(slug!);
          if (!cancelled) setPrograms(r.items);
        } else if (tab === 'articles') {
          const r = await api.articles(slug!);
          if (!cancelled) setArticles(r.items);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (!cancelled) setTabLoading(false);
      }
    }

    void loadTab();
    return () => {
      cancelled = true;
    };
  }, [slug, tab, candidate, interviews, programs, articles]);

  const votesByChamber = useMemo(() => {
    const list = votes || [];
    const map: Record<string, ParliamentaryVote[]> = {
      assemblee: [],
      senat: [],
      parlement_europeen: [],
    };
    for (const v of list) {
      const key = v.chamber in map ? v.chamber : 'assemblee';
      map[key].push(v);
    }
    return map;
  }, [votes]);

  const filteredVotes = useMemo(() => {
    if (!votes) return [];
    if (chamber === 'all') return votes;
    return votesByChamber[chamber] || [];
  }, [votes, chamber, votesByChamber]);

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

      {tabLoading && <Loading />}

      {tab === 'votes' && votes === null && !tabLoading && <Loading />}

      {tab === 'votes' && votes !== null && !tabLoading && (
        <section className="vote-space">
          <div className="chamber-tabs">
            <button
              type="button"
              className={chamber === 'all' ? 'active' : ''}
              onClick={() => setChamber('all')}
            >
              Tous ({votes?.length || 0})
            </button>
            <button
              type="button"
              className={chamber === 'assemblee' ? 'active' : ''}
              onClick={() => setChamber('assemblee')}
            >
              Assemblée ({votesByChamber.assemblee.length})
            </button>
            <button
              type="button"
              className={chamber === 'senat' ? 'active' : ''}
              onClick={() => setChamber('senat')}
            >
              Sénat ({votesByChamber.senat.length})
            </button>
            <button
              type="button"
              className={chamber === 'parlement_europeen' ? 'active' : ''}
              onClick={() => setChamber('parlement_europeen')}
            >
              Europe ({votesByChamber.parlement_europeen.length})
            </button>
          </div>

          {chamber === 'parlement_europeen' && votesByChamber.parlement_europeen.length === 0 && (
            <p className="empty-state">
              Les votes du Parlement européen ne sont pas encore collectés (CLAIR.vote
              couvre l’Assemblée et le Sénat uniquement).
            </p>
          )}

          {chamber === 'senat' && votesByChamber.senat.length === 0 && (
            <p className="empty-state">
              Aucun vote au Sénat pour ce candidat (pas de matching sénateur CLAIR, ou pas
              encore ingéré).
            </p>
          )}

          {filteredVotes.length > 0 && (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Chambre</th>
                  <th>Scrutin</th>
                  <th>Position</th>
                  <th>Groupe</th>
                  <th>Aligné</th>
                  <th>Date</th>
                  <th>Source</th>
                </tr>
              </thead>
              <tbody>
                {filteredVotes.map((v) => (
                  <tr key={v.id}>
                    <td>
                      <span className="chamber-pill">
                        {CHAMBER_LABELS[v.chamber] || v.chamber}
                      </span>
                      {v.parliamentary_group && (
                        <div className="vote-group-inline">
                          <GroupBadge
                            name={v.parliamentary_group.name}
                            color={v.parliamentary_group.color}
                            to={`/groups/${v.parliamentary_group.slug}`}
                          />
                        </div>
                      )}
                    </td>
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
                      <SourceLink url={clairScrutinUrl(v)} label="CLAIR" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {chamber === 'all' && filteredVotes.length === 0 && (
            <p className="empty-state">Aucun vote collecté</p>
          )}
          {chamber === 'assemblee' && votesByChamber.assemblee.length === 0 && (
            <p className="empty-state">Aucun vote à l’Assemblée collecté</p>
          )}
        </section>
      )}

      {tab === 'interventions' && !tabLoading && (
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
            {(interviews || []).map((i) => (
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
            {(interviews || []).length === 0 && (
              <tr>
                <td colSpan={5}>Aucune intervention collectée</td>
              </tr>
            )}
          </tbody>
        </table>
      )}

      {tab === 'programme' && !tabLoading && (
        <div className="program-list">
          {(programs || []).map((p) => {
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
          {(programs || []).length === 0 && (
            <p className="empty-state">Aucun document de programme</p>
          )}
        </div>
      )}

      {tab === 'articles' && !tabLoading && (
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
            {(articles || []).map((a) => {
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
            {(articles || []).length === 0 && (
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
