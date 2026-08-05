import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { api, Candidate } from '../api/client';
import { ErrorMessage, GroupBadge, Loading } from '../components/Layout';

const STATUS_LABELS: Record<string, string> = {
  potential: 'Potentiel',
  declared: 'Déclaré',
  withdrawn: 'Retiré',
};

const STATUS_ORDER = ['declared', 'potential', 'withdrawn'] as const;

type SortKey = 'name' | 'party' | 'status' | 'group';

const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: 'name', label: 'Nom' },
  { value: 'party', label: 'Parti' },
  { value: 'status', label: 'Statut' },
  { value: 'group', label: 'Groupe AN' },
];

const NONE = '__none__';

function compareText(a: string, b: string): number {
  return a.localeCompare(b, 'fr', { sensitivity: 'base' });
}

function sortCandidates(list: Candidate[], sortBy: SortKey, sortDir: 'asc' | 'desc'): Candidate[] {
  const dir = sortDir === 'asc' ? 1 : -1;
  return [...list].sort((a, b) => {
    let cmp = 0;
    if (sortBy === 'name') {
      cmp = compareText(a.full_name, b.full_name);
    } else if (sortBy === 'party') {
      cmp = compareText(a.party || 'zzz', b.party || 'zzz');
      if (cmp === 0) cmp = compareText(a.full_name, b.full_name);
    } else if (sortBy === 'status') {
      const ai = STATUS_ORDER.indexOf(a.status as (typeof STATUS_ORDER)[number]);
      const bi = STATUS_ORDER.indexOf(b.status as (typeof STATUS_ORDER)[number]);
      cmp = (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
      if (cmp === 0) cmp = compareText(a.full_name, b.full_name);
    } else {
      cmp = compareText(
        a.parliamentary_group?.name || 'zzz',
        b.parliamentary_group?.name || 'zzz',
      );
      if (cmp === 0) cmp = compareText(a.full_name, b.full_name);
    }
    return cmp * dir;
  });
}

export function CandidatesPage() {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const query = searchParams.get('q') || '';
  const partyFilter = searchParams.get('party') || 'all';
  const statusFilter = searchParams.get('status') || 'all';
  const groupFilter = searchParams.get('group') || 'all';
  const sortBy = (searchParams.get('sort') as SortKey) || 'name';
  const sortDir = searchParams.get('dir') === 'desc' ? 'desc' : 'asc';

  function updateParam(key: string, value: string, defaultValue = 'all') {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (!value || value === defaultValue) {
          next.delete(key);
        } else {
          next.set(key, value);
        }
        return next;
      },
      { replace: true },
    );
  }

  useEffect(() => {
    api
      .candidates()
      .then(setCandidates)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const parties = useMemo(() => {
    const set = new Set<string>();
    let hasNone = false;
    for (const c of candidates) {
      if (c.party) set.add(c.party);
      else hasNone = true;
    }
    const list = Array.from(set).sort((a, b) => compareText(a, b));
    return { list, hasNone };
  }, [candidates]);

  const groups = useMemo(() => {
    const map = new Map<string, string>();
    let hasNone = false;
    for (const c of candidates) {
      if (c.parliamentary_group) {
        map.set(c.parliamentary_group.slug, c.parliamentary_group.name);
      } else {
        hasNone = true;
      }
    }
    const list = Array.from(map.entries())
      .map(([slug, name]) => ({ slug, name }))
      .sort((a, b) => compareText(a.name, b.name));
    return { list, hasNone };
  }, [candidates]);

  const statuses = useMemo(() => {
    const present = new Set(candidates.map((c) => c.status));
    const known = STATUS_ORDER.filter((s) => present.has(s));
    const extra = Array.from(present).filter(
      (s) => !STATUS_ORDER.includes(s as (typeof STATUS_ORDER)[number]),
    );
    return [...known, ...extra];
  }, [candidates]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = candidates.filter((c) => {
      if (q) {
        const hay = `${c.full_name} ${c.party || ''} ${c.parliamentary_group?.name || ''}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      if (partyFilter === NONE) {
        if (c.party) return false;
      } else if (partyFilter !== 'all' && c.party !== partyFilter) {
        return false;
      }
      if (statusFilter !== 'all' && c.status !== statusFilter) return false;
      if (groupFilter === NONE) {
        if (c.parliamentary_group) return false;
      } else if (groupFilter !== 'all' && c.parliamentary_group?.slug !== groupFilter) {
        return false;
      }
      return true;
    });
    const validSort: SortKey = SORT_OPTIONS.some((o) => o.value === sortBy) ? sortBy : 'name';
    return sortCandidates(list, validSort, sortDir);
  }, [candidates, query, partyFilter, statusFilter, groupFilter, sortBy, sortDir]);

  const hasActiveFilters =
    Boolean(query.trim()) ||
    partyFilter !== 'all' ||
    statusFilter !== 'all' ||
    groupFilter !== 'all';

  function resetFilters() {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams();
        const sort = prev.get('sort');
        const dir = prev.get('dir');
        if (sort && sort !== 'name') next.set('sort', sort);
        if (dir === 'desc') next.set('dir', dir);
        return next;
      },
      { replace: true },
    );
  }

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
        <>
          <div className="candidate-filters" role="search" aria-label="Filtres candidats">
            <label className="form-field candidate-filter-search">
              <span>Rechercher</span>
              <input
                type="search"
                value={query}
                onChange={(e) => updateParam('q', e.target.value, '')}
                placeholder="Nom, parti, groupe…"
                aria-label="Rechercher un candidat"
              />
            </label>

            <label className="form-field">
              <span>Parti</span>
              <select
                value={partyFilter}
                onChange={(e) => updateParam('party', e.target.value)}
                aria-label="Filtrer par parti"
              >
                <option value="all">Tous les partis</option>
                {parties.list.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
                {parties.hasNone && <option value={NONE}>Parti non renseigné</option>}
              </select>
            </label>

            <label className="form-field">
              <span>Statut</span>
              <select
                value={statusFilter}
                onChange={(e) => updateParam('status', e.target.value)}
                aria-label="Filtrer par statut"
              >
                <option value="all">Tous les statuts</option>
                {statuses.map((s) => (
                  <option key={s} value={s}>
                    {STATUS_LABELS[s] || s}
                  </option>
                ))}
              </select>
            </label>

            <label className="form-field">
              <span>Groupe AN</span>
              <select
                value={groupFilter}
                onChange={(e) => updateParam('group', e.target.value)}
                aria-label="Filtrer par groupe parlementaire"
              >
                <option value="all">Tous les groupes</option>
                {groups.list.map((g) => (
                  <option key={g.slug} value={g.slug}>
                    {g.name}
                  </option>
                ))}
                {groups.hasNone && <option value={NONE}>Pas de groupe AN</option>}
              </select>
            </label>

            <label className="form-field">
              <span>Trier par</span>
              <div className="candidate-sort-controls">
                <select
                  value={SORT_OPTIONS.some((o) => o.value === sortBy) ? sortBy : 'name'}
                  onChange={(e) => updateParam('sort', e.target.value, 'name')}
                  aria-label="Critère de tri"
                >
                  {SORT_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  className="btn btn-secondary sort-dir-btn"
                  onClick={() => updateParam('dir', sortDir === 'asc' ? 'desc' : 'asc', 'asc')}
                  aria-label={sortDir === 'asc' ? 'Tri croissant' : 'Tri décroissant'}
                  title={sortDir === 'asc' ? 'Croissant' : 'Décroissant'}
                >
                  {sortDir === 'asc' ? '↑' : '↓'}
                </button>
              </div>
            </label>
          </div>

          <div className="candidate-filter-summary">
            <p className="muted">
              {filtered.length} candidat{filtered.length > 1 ? 's' : ''}
              {hasActiveFilters ? ` sur ${candidates.length}` : ''}
            </p>
            {hasActiveFilters && (
              <button type="button" className="link-btn" onClick={resetFilters}>
                Réinitialiser les filtres
              </button>
            )}
          </div>

          {filtered.length === 0 ? (
            <p className="empty-state">
              Aucun candidat ne correspond à ces filtres.{' '}
              <button type="button" className="link-btn" onClick={resetFilters}>
                Tout afficher
              </button>
            </p>
          ) : (
            <div className="candidate-list">
              {filtered.map((c) => (
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
        </>
      )}
    </div>
  );
}
