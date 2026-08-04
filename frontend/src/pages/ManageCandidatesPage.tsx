import { FormEvent, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, Candidate } from '../api/client';
import { ErrorMessage, GroupBadge, Loading } from '../components/Layout';

const SECRET_KEY = 'factchecker_ingestion_secret';

export function ManageCandidatesPage() {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [secret, setSecret] = useState(() => sessionStorage.getItem(SECRET_KEY) || '');
  const [fullName, setFullName] = useState('');
  const [party, setParty] = useState('');
  const [status, setStatus] = useState<'declared' | 'potential' | 'withdrawn'>('potential');
  const [slug, setSlug] = useState('');
  const [clairSlug, setClairSlug] = useState('');

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
        party: party.trim() || null,
        status,
        slug: slug.trim() || null,
        clair_slug: clairSlug.trim() || null,
      });
      setMessage(`Candidat « ${created.full_name} » ajouté (${created.slug}).`);
      setFullName('');
      setParty('');
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

  async function handleSeed() {
    if (!secret.trim()) {
      setError('Renseigne le secret d’ingestion avant d’importer le seed.');
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await api.seedCandidates(secret.trim());
      setMessage(
        `Seed importé : ${result.created} créé(s), ${result.updated} mis à jour, ${result.total} au total.`,
      );
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
        Ajoute ou supprime des candidats en base de production. Protégé par le secret
        d’ingestion Render.
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
        <div className="admin-panel-header">
          <h2>Importer le seed YAML</h2>
          <button type="button" className="btn" onClick={handleSeed} disabled={busy}>
            Importer les 10 candidats du seed
          </button>
        </div>
        <p className="muted">
          Utile pour peupler une base vide à partir de{' '}
          <code>backend/seeds/candidates.yaml</code>. Idempotent.
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
          <label className="form-field">
            <span>Parti</span>
            <input
              value={party}
              onChange={(e) => setParty(e.target.value)}
              placeholder="RE"
            />
          </label>
          <label className="form-field">
            <span>Statut</span>
            <select value={status} onChange={(e) => setStatus(e.target.value as typeof status)}>
              <option value="potential">potential</option>
              <option value="declared">declared</option>
              <option value="withdrawn">withdrawn</option>
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
            <span>Slug CLAIR.vote (optionnel)</span>
            <input
              value={clairSlug}
              onChange={(e) => setClairSlug(e.target.value)}
              placeholder="gabriel-attal"
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
          <p className="empty-state">Aucun candidat. Importe le seed ou ajoute-en un.</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Nom</th>
                <th>Parti</th>
                <th>Groupe AN</th>
                <th>Statut</th>
                <th>CLAIR</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {candidates.map((c) => (
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
                  <td className="muted">{c.external_ids?.clair_slug || '—'}</td>
                  <td>
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
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
