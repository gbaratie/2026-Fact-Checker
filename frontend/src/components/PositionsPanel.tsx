import { FormEvent, useEffect, useMemo, useState } from 'react';
import {
  api,
  CandidateCoherence,
  Claim,
  ClaimStance,
  COHERENCE_LABELS,
  CoherenceStatus,
  EvidenceType,
  ParliamentaryVote,
  STANCE_LABELS,
  Topic,
} from '../api/client';
import { ErrorMessage, Loading, SourceLink } from './Layout';

const SECRET_KEY = 'factchecker_ingestion_secret';

const STANCES: ClaimStance[] = ['pour', 'contre', 'nuance', 'inconnu'];
const EVIDENCE_TYPES: { value: EvidenceType; label: string }[] = [
  { value: 'manual', label: 'Saisie manuelle' },
  { value: 'interview', label: 'Interview' },
  { value: 'program', label: 'Programme' },
  { value: 'article', label: 'Article' },
  { value: 'other', label: 'Autre' },
];

function coherenceClass(status: CoherenceStatus): string {
  if (status === 'aligned') return 'coherence-aligned';
  if (status === 'conflict') return 'coherence-conflict';
  if (status === 'mixed') return 'coherence-mixed';
  return 'coherence-neutral';
}

export function PositionsPanel({
  slug,
  votes,
  claimCount,
  onClaimsChanged,
  onVoteTopicsChanged,
}: {
  slug: string;
  votes: ParliamentaryVote[] | null;
  claimCount: number;
  onClaimsChanged: (count: number) => void;
  onVoteTopicsChanged: () => void;
}) {
  const [topics, setTopics] = useState<Topic[] | null>(null);
  const [claims, setClaims] = useState<Claim[] | null>(null);
  const [coherence, setCoherence] = useState<CandidateCoherence | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [secret, setSecret] = useState(() => sessionStorage.getItem(SECRET_KEY) || '');
  const [topicSlug, setTopicSlug] = useState('');
  const [stance, setStance] = useState<ClaimStance>('pour');
  const [summary, setSummary] = useState('');
  const [quote, setQuote] = useState('');
  const [sourceUrl, setSourceUrl] = useState('');
  const [evidenceType, setEvidenceType] = useState<EvidenceType>('manual');

  const [tagVoteId, setTagVoteId] = useState('');
  const [tagTopicSlugs, setTagTopicSlugs] = useState<string[]>([]);

  async function refresh() {
    setError(null);
    try {
      const [topicList, claimList, coherenceData] = await Promise.all([
        api.topics(),
        api.claims(slug),
        api.coherence(slug),
      ]);
      setTopics(topicList);
      setClaims(claimList);
      setCoherence(coherenceData);
      onClaimsChanged(claimList.length);
      if (!topicSlug && topicList.length) setTopicSlug(topicList[0].slug);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug]);

  useEffect(() => {
    if (!tagVoteId || !votes) return;
    const vote = votes.find((v) => v.id === tagVoteId);
    setTagTopicSlugs(vote?.topics?.map((t) => t.slug) || []);
  }, [tagVoteId, votes]);

  const voteOptions = useMemo(() => votes || [], [votes]);

  function persistSecret(value: string) {
    setSecret(value);
    if (value) sessionStorage.setItem(SECRET_KEY, value);
    else sessionStorage.removeItem(SECRET_KEY);
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!secret.trim()) {
      setError('Secret d’ingestion requis pour ajouter une position.');
      return;
    }
    if (!summary.trim() || !topicSlug) {
      setError('Thème et résumé sont obligatoires.');
      return;
    }

    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await api.createClaim(secret.trim(), slug, {
        topic_slug: topicSlug,
        stance,
        summary: summary.trim(),
        quote: quote.trim() || null,
        source_url: sourceUrl.trim() || null,
        evidence_type: evidenceType,
        method: 'manual',
      });
      setMessage('Position enregistrée.');
      setSummary('');
      setQuote('');
      setSourceUrl('');
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(claimId: string) {
    if (!secret.trim()) {
      setError('Secret d’ingestion requis pour supprimer.');
      return;
    }
    if (!window.confirm('Supprimer cette position ?')) return;
    setBusy(true);
    setError(null);
    try {
      await api.deleteClaim(secret.trim(), claimId);
      setMessage('Position supprimée.');
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleTagVote(e: FormEvent) {
    e.preventDefault();
    if (!secret.trim()) {
      setError('Secret d’ingestion requis pour taguer un vote.');
      return;
    }
    if (!tagVoteId) {
      setError('Choisis un vote à taguer.');
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await api.setVoteTopics(secret.trim(), tagVoteId, tagTopicSlugs);
      setMessage('Thèmes du vote mis à jour.');
      onVoteTopicsChanged();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  function toggleTagTopic(slugValue: string) {
    setTagTopicSlugs((prev) =>
      prev.includes(slugValue) ? prev.filter((s) => s !== slugValue) : [...prev, slugValue],
    );
  }

  if (error && !claims) return <ErrorMessage message={error} />;
  if (!claims || !topics || !coherence) return <Loading />;

  return (
    <section className="positions-panel">
      <p className="home-section-lead">
        Positions structurées par thème, comparées aux votes tagués. Ce n’est pas une note
        automatique : chaque claim est saisie (ou sera extraite) avec une source.
      </p>

      {error && <ErrorMessage message={error} />}
      {message && <p className="success-banner">{message}</p>}

      <h3 className="section-title">Cohérence déclaration ↔ vote</h3>
      {coherence.topics.length === 0 ? (
        <p className="empty-state">
          Aucun thème comparable pour l’instant ({claimCount} position
          {claimCount === 1 ? '' : 's'}). Ajoute une déclaration et tague des votes.
        </p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Thème</th>
              <th>Statut</th>
              <th>Déclarations</th>
              <th>Votes</th>
            </tr>
          </thead>
          <tbody>
            {coherence.topics.map((row) => (
              <tr key={row.topic.id}>
                <td>
                  <strong>{row.topic.label}</strong>
                </td>
                <td>
                  <span className={`coherence-badge ${coherenceClass(row.status)}`}>
                    {COHERENCE_LABELS[row.status]}
                  </span>
                </td>
                <td>
                  {row.claims_count} · {row.claim_stances.join(', ') || '—'}
                </td>
                <td>
                  {row.votes_count} · {row.vote_positions.join(', ') || '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h3 className="section-title">Positions enregistrées</h3>
      {claims.length === 0 ? (
        <p className="empty-state">Aucune position structurée pour ce candidat.</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Thème</th>
              <th>Stance</th>
              <th>Résumé</th>
              <th>Preuve</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {claims.map((claim) => (
              <tr key={claim.id}>
                <td>{claim.topic.label}</td>
                <td>
                  <span className={`vote-${claim.stance}`}>
                    {STANCE_LABELS[claim.stance as ClaimStance] || claim.stance}
                  </span>
                </td>
                <td>
                  <div>{claim.summary}</div>
                  {claim.quote && <p className="muted claim-quote">« {claim.quote} »</p>}
                </td>
                <td>
                  <span className="muted">{claim.evidence_type}</span>
                  {claim.source_url && (
                    <>
                      {' · '}
                      <SourceLink url={claim.source_url} label="Source" />
                    </>
                  )}
                </td>
                <td>
                  <button
                    type="button"
                    className="btn-danger btn-small"
                    disabled={busy}
                    onClick={() => void handleDelete(claim.id)}
                  >
                    Suppr.
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <div className="admin-panel" style={{ marginTop: '1.5rem' }}>
        <h2>Ajouter une position</h2>
        <form className="admin-form" onSubmit={handleCreate}>
          <label className="form-field">
            Secret d’ingestion
            <input
              type="password"
              value={secret}
              onChange={(e) => persistSecret(e.target.value)}
              autoComplete="off"
              placeholder="INGESTION_SECRET"
            />
          </label>
          <label className="form-field">
            Thème
            <select value={topicSlug} onChange={(e) => setTopicSlug(e.target.value)} required>
              {topics.map((t) => (
                <option key={t.id} value={t.slug}>
                  {t.label}
                </option>
              ))}
            </select>
          </label>
          <label className="form-field">
            Stance
            <select
              value={stance}
              onChange={(e) => setStance(e.target.value as ClaimStance)}
            >
              {STANCES.map((s) => (
                <option key={s} value={s}>
                  {STANCE_LABELS[s]}
                </option>
              ))}
            </select>
          </label>
          <label className="form-field">
            Type de preuve
            <select
              value={evidenceType}
              onChange={(e) => setEvidenceType(e.target.value as EvidenceType)}
            >
              {EVIDENCE_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </label>
          <label className="form-field" style={{ gridColumn: '1 / -1' }}>
            Résumé
            <input
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              required
              minLength={3}
              placeholder="Ex. Favorable à un durcissement des conditions d’asile"
            />
          </label>
          <label className="form-field" style={{ gridColumn: '1 / -1' }}>
            Citation (optionnel)
            <input
              value={quote}
              onChange={(e) => setQuote(e.target.value)}
              placeholder="Extrait verbatim"
            />
          </label>
          <label className="form-field" style={{ gridColumn: '1 / -1' }}>
            URL source (optionnel)
            <input
              value={sourceUrl}
              onChange={(e) => setSourceUrl(e.target.value)}
              placeholder="https://…"
            />
          </label>
          <div>
            <button type="submit" className="btn" disabled={busy}>
              Enregistrer
            </button>
          </div>
        </form>
      </div>

      <div className="admin-panel">
        <h2>Taguer un vote par thème</h2>
        <p className="muted" style={{ marginBottom: '0.75rem' }}>
          Sans tag thématique, un vote ne peut pas entrer dans la comparaison de cohérence.
        </p>
        {voteOptions.length === 0 ? (
          <p className="empty-state">Charge d’abord l’onglet Votes (aucun vote disponible).</p>
        ) : (
          <form className="admin-form" onSubmit={handleTagVote}>
            <label className="form-field" style={{ gridColumn: '1 / -1' }}>
              Vote
              <select
                value={tagVoteId}
                onChange={(e) => setTagVoteId(e.target.value)}
                required
              >
                <option value="">— Choisir —</option>
                {voteOptions.map((v) => (
                  <option key={v.id} value={v.id}>
                    [{v.position}] {v.title.slice(0, 80)}
                    {v.title.length > 80 ? '…' : ''}
                  </option>
                ))}
              </select>
            </label>
            <div className="form-field" style={{ gridColumn: '1 / -1' }}>
              <span>Thèmes</span>
              <div className="topic-checkboxes">
                {topics.map((t) => (
                  <label key={t.id} className="topic-check">
                    <input
                      type="checkbox"
                      checked={tagTopicSlugs.includes(t.slug)}
                      onChange={() => toggleTagTopic(t.slug)}
                    />
                    {t.label}
                  </label>
                ))}
              </div>
            </div>
            <div>
              <button type="submit" className="btn" disabled={busy || !tagVoteId}>
                Enregistrer les thèmes
              </button>
            </div>
          </form>
        )}
      </div>
    </section>
  );
}
