import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  api,
  Candidate,
  CandidateStatus,
  clairDeputeUrl,
  KNOWN_PARTIES,
} from '../api/client';
import { ErrorMessage, GroupBadge, Loading } from '../components/Layout';

const SECRET_KEY = 'factchecker_ingestion_secret';
const CUSTOM_PARTY = '__custom__';

const STATUS_OPTIONS: { value: CandidateStatus; label: string }[] = [
  { value: 'potential', label: 'Potentiel' },
  { value: 'declared', label: 'Déclaré' },
  { value: 'withdrawn', label: 'Retiré' },
];

export function ManageCandidatesPage() {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [secret, setSecret] = useState(() => sessionStorage.getItem(SECRET_KEY) || '');
  const [fullName, setFullName] = useState('');
  const [partyChoice, setPartyChoice] = useState('');
  const [customParty, setCustomParty] = useState('');
  const [status, setStatus] = useState<CandidateStatus>('potential');
  const [slug, setSlug] = useState('');
  const [clairSlug, setClairSlug] = useState('');

  const [editingSlug, setEditingSlug] = useState<string | null>(null);
  const [editPartyChoice, setEditPartyChoice] = useState('');
  const [editCustomParty, setEditCustomParty] = useState('');
  const [editStatus, setEditStatus] = useState<CandidateStatus>('potential');
  const [editClairSlug, setEditClairSlug] = useState('');

  const knownParties = useMemo(() => {
    const fromDb = candidates.map((c) => c.party).filter((p): p is string => Boolean(p));
    return Array.from(new Set([...KNOWN_PARTIES, ...fromDb])).sort((a, b) =>
      a.localeCompare(b, 'fr'),
    );
  }, [candidates]);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      setCandidates(await api.candidates());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  function persistSecret(value: string) {
    setSecret(value);
    if (value) sessionStorage.setItem(SECRET_KEY, value);
    else sessionStorage.removeItem(SECRET_KEY);
  }

  function resolveParty(choice: string, custom: string): string | null {
    if (choice === CUSTOM_PARTY) return custom.trim() || null;
    return choice.trim() || null;
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!secret.trim()) {
      setError('Renseigne le secret d’ingestion (variable INGESTION_SECRET sur Render).');
      return;
    }
    if (!fullName.trim()) {
      setError('Le nom complet est obligatoire.');
      return;
    }

    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const created = await api.createCandidate(secret.trim(), {
        full_name: fullName.trim(),
        party: resolveParty(partyChoice, customParty),
        status,
        slug: slug.trim() || null,
        clair_slug: clairSlug.trim() || null,
      });
      setMessage(`Candidat « ${created.full_name} » ajouté (${created.slug}).`);
      setFullName('');
      setPartyChoice('');
      setCustomParty('');
      setSlug('');
      setClairSlug('');
      setStatus('potential');
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  function startEdit(candidate: Candidate) {
    setEditingSlug(candidate.slug);
    const party = candidate.party || '';
    if (party && knownParties.includes(party)) {
      setEditPartyChoice(party);
      setEditCustomParty('');
    } else if (party) {
      setEditPartyChoice(CUSTOM_PARTY);
      setEditCustomParty(party);
    } else {
      setEditPartyChoice('');
      setEditCustomParty('');
    }
    setEditStatus((candidate.status as CandidateStatus) || 'potential');
    setEditClairSlug(candidate.external_ids?.clair_slug || '');
    setMessage(null);
    setError(null);
  }

  async function handleSaveEdit(candidate: Candidate) {
    if (!secret.trim()) {
      setError('Renseigne le secret d’ingestion avant de modifier.');
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const updated = await api.updateCandidate(secret.trim(), candidate.slug, {
        party: resolveParty(editPartyChoice, editCustomParty),
        status: editStatus,
        clair_slug: editClairSlug.trim() || null,
      });
      setMessage(`Candidat « ${updated.full_name} » mis à jour.`);
      setEditingSlug(null);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(candidate: Candidate) {
    if (!secret.trim()) {
      setError('Renseigne le secret d’ingestion avant de supprimer.');
      return;
    }
    const ok = window.confirm(
      `Supprimer « ${candidate.full_name} » et toutes ses données liées (votes, articles, etc.) ?`,
    );
    if (!ok) return;

    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await api.deleteCandidate(secret.trim(), candidate.slug);
      setMessage(`Candidat « ${candidate.full_name} » supprimé.`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1>Gestion des candidats</h1>
      <p className="subtitle">
        Ajoute, modifie ou supprime des candidats. Protégé par le secret d’ingestion Render.
      </p>

      <section className="admin-panel">
        <h2>Accès admin</h2>
        <label className="form-field">
          <span>Secret d’ingestion (`INGESTION_SECRET`)</span>
          <input
            type="password"
            autoComplete="off"
            value={secret}
            onChange={(e) => persistSecret(e.target.value)}
            placeholder="Coller le secret Render"
          />
        </label>
        <p className="muted">
          Stocké uniquement dans cette session navigateur. Visible dans le dashboard Render
          → service API → Environment.
        </p>
      </section>

      <section className="admin-panel">
        <h2>Ajouter un candidat</h2>
        <form className="admin-form" onSubmit={handleCreate}>
          <label className="form-field">
            <span>Nom complet *</span>
            <input
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Gabriel Attal"
              required
            />
          </label>
          <PartySelect
            label="Parti"
            choice={partyChoice}
            custom={customParty}
            parties={knownParties}
            onChoice={setPartyChoice}
            onCustom={setCustomParty}
          />
          <label className="form-field">
            <span>Statut</span>
            <select value={status} onChange={(e) => setStatus(e.target.value as CandidateStatus)}>
              {STATUS_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
          <label className="form-field">
            <span>Slug (optionnel)</span>
            <input
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              placeholder="gabriel-attal"
            />
          </label>
          <label className="form-field">
            <span className="label-with-info">
              Slug CLAIR.vote
              <InfoTip text="Identifiant du député sur clair.vote (ex. francois-ruffin). Sert à récupérer automatiquement les votes à l’Assemblée. Laisser vide pour tenter un matching par nom." />
            </span>
            <input
              value={clairSlug}
              onChange={(e) => setClairSlug(e.target.value)}
              placeholder="francois-ruffin"
            />
          </label>
          <button type="submit" className="btn" disabled={busy}>
            Ajouter
          </button>
        </form>
      </section>

      {error && <ErrorMessage message={error} />}
      {message && <p className="success-banner">{message}</p>}

      <section>
        <h2 className="section-title">Candidats en base ({candidates.length})</h2>
        {loading ? (
          <Loading />
        ) : candidates.length === 0 ? (
          <p className="empty-state">Aucun candidat. Ajoute-en un ci-dessus.</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Nom</th>
                <th>Parti</th>
                <th>Groupe AN</th>
                <th>Statut</th>
                <th>
                  <span className="label-with-info">
                    CLAIR
                    <InfoTip text="Lien vers la fiche député sur clair.vote, source des votes Assemblée (et Sénat si disponible)." />
                  </span>
                </th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {candidates.map((c) => {
                const isEditing = editingSlug === c.slug;
                const clairUrl = clairDeputeUrl(c.external_ids?.clair_slug);
                if (isEditing) {
                  return (
                    <tr key={c.id} className="row-editing">
                      <td>
                        <Link to={`/candidates/${c.slug}`}>{c.full_name}</Link>
                      </td>
                      <td colSpan={2}>
                        <div className="inline-edit-grid">
                          <PartySelect
                            label=""
                            choice={editPartyChoice}
                            custom={editCustomParty}
                            parties={knownParties}
                            onChoice={setEditPartyChoice}
                            onCustom={setEditCustomParty}
                            compact
                          />
                        </div>
                      </td>
                      <td>
                        <select
                          value={editStatus}
                          onChange={(e) => setEditStatus(e.target.value as CandidateStatus)}
                        >
                          {STATUS_OPTIONS.map((o) => (
                            <option key={o.value} value={o.value}>
                              {o.label}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td>
                        <input
                          value={editClairSlug}
                          onChange={(e) => setEditClairSlug(e.target.value)}
                          placeholder="slug-clair"
                          className="inline-input"
                        />
                      </td>
                      <td className="row-actions">
                        <button
                          type="button"
                          className="btn"
                          disabled={busy}
                          onClick={() => void handleSaveEdit(c)}
                        >
                          Enregistrer
                        </button>
                        <button
                          type="button"
                          className="btn-secondary btn-small"
                          disabled={busy}
                          onClick={() => setEditingSlug(null)}
                        >
                          Annuler
                        </button>
                      </td>
                    </tr>
                  );
                }
                return (
                  <tr key={c.id}>
                    <td>
                      <Link to={`/candidates/${c.slug}`}>{c.full_name}</Link>
                    </td>
                    <td>{c.party || '—'}</td>
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
                      {clairUrl ? (
                        <a href={clairUrl} target="_blank" rel="noopener noreferrer" className="source-link">
                          {c.external_ids.clair_slug}
                        </a>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                    <td className="row-actions">
                      <button
                        type="button"
                        className="btn-secondary btn-small"
                        disabled={busy}
                        onClick={() => startEdit(c)}
                      >
                        Modifier
                      </button>
                      <button
                        type="button"
                        className="btn-danger"
                        disabled={busy}
                        onClick={() => void handleDelete(c)}
                      >
                        Supprimer
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

function PartySelect({
  label,
  choice,
  custom,
  parties,
  onChoice,
  onCustom,
  compact,
}: {
  label: string;
  choice: string;
  custom: string;
  parties: string[];
  onChoice: (v: string) => void;
  onCustom: (v: string) => void;
  compact?: boolean;
}) {
  return (
    <label className={`form-field ${compact ? 'form-field-compact' : ''}`}>
      {label ? <span>{label}</span> : null}
      <select value={choice} onChange={(e) => onChoice(e.target.value)}>
        <option value="">— Aucun —</option>
        {parties.map((p) => (
          <option key={p} value={p}>
            {p}
          </option>
        ))}
        <option value={CUSTOM_PARTY}>Autre…</option>
      </select>
      {choice === CUSTOM_PARTY && (
        <input
          value={custom}
          onChange={(e) => onCustom(e.target.value)}
          placeholder="Nom du parti"
        />
      )}
    </label>
  );
}

function InfoTip({ text }: { text: string }) {
  return (
    <span className="info-tip" title={text} tabIndex={0} aria-label={text}>
      i
    </span>
  );
}
