const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface Source {
  id: string;
  source_type: string;
  url: string;
  publisher: string | null;
  fetched_at: string;
  raw_metadata?: Record<string, string | number | null>;
}

export interface ParliamentaryGroup {
  id: string;
  slug: string;
  name: string;
  full_name: string;
  color: string | null;
  chamber: string;
  legislature: number | null;
  spectrum: string | null;
}

export interface VoteStats {
  total: number;
  pour: number;
  contre: number;
  abstention: number;
  other: number;
  with_group_position: number;
  aligned_with_group: number;
  loyalty_rate: number | null;
}

export interface Candidate {
  id: string;
  slug: string;
  full_name: string;
  party: string | null;
  external_ids: Record<string, string>;
  status: string;
  parliamentary_group: ParliamentaryGroup | null;
}

export interface CandidateDetail extends Candidate {
  interview_count: number;
  program_count: number;
  vote_count: number;
  article_count: number;
  claim_count: number;
  vote_stats: VoteStats | null;
}

export interface Topic {
  id: string;
  slug: string;
  label: string;
  description: string | null;
  sort_order: number;
}

export type ClaimStance = 'pour' | 'contre' | 'nuance' | 'inconnu';
export type EvidenceType = 'interview' | 'program' | 'article' | 'manual' | 'other';

export interface Claim {
  id: string;
  candidate_id: string;
  topic: Topic;
  stance: ClaimStance | string;
  summary: string;
  quote: string | null;
  evidence_type: EvidenceType | string;
  interview_id: string | null;
  program_document_id: string | null;
  article_id: string | null;
  source_url: string | null;
  method: string;
  confidence: number | null;
  created_at: string;
  updated_at: string;
}

export interface ClaimCreateInput {
  topic_slug: string;
  stance: ClaimStance;
  summary: string;
  quote?: string | null;
  evidence_type?: EvidenceType;
  interview_id?: string | null;
  program_document_id?: string | null;
  article_id?: string | null;
  source_url?: string | null;
  method?: 'manual' | 'llm' | 'rule';
  confidence?: number | null;
}

export type CoherenceStatus =
  | 'aligned'
  | 'conflict'
  | 'mixed'
  | 'abstention_only'
  | 'claims_only'
  | 'votes_only'
  | 'empty';

export interface TopicCoherence {
  topic: Topic;
  status: CoherenceStatus;
  claim_stances: string[];
  vote_positions: string[];
  claims_count: number;
  votes_count: number;
}

export interface CandidateCoherence {
  candidate_slug: string;
  topics: TopicCoherence[];
}

export interface LlmClassifyVotesResult {
  classified: number;
  skipped: number;
  processed: number;
  errors: string[];
}

export interface LlmExtractClaimsResult {
  created: number;
  skipped: number;
  programs_processed: number;
  errors: string[];
}

export interface Interview {
  id: string;
  youtube_video_id: string;
  title: string;
  channel_name: string | null;
  transcript: string | null;
  published_at: string | null;
  source: Source;
}

export interface ParliamentaryVote {
  id: string;
  chamber: string;
  scrutin_id: string;
  title: string;
  position: string;
  group_position: string | null;
  aligned_with_group: boolean | null;
  vote_date: string | null;
  source: Source;
  parliamentary_group: ParliamentaryGroup | null;
  topics: Topic[];
}

export interface Article {
  id: string;
  title: string;
  url: string;
  publisher: string | null;
  excerpt: string | null;
  published_at: string | null;
  source: Source;
}

export interface ProgramDocument {
  id: string;
  title: string;
  url: string;
  kind: string;
  year: number | null;
  publisher: string | null;
  excerpt: string | null;
  note: string | null;
  source: Source;
}

export interface GroupMember {
  id: string;
  slug: string;
  full_name: string;
  party: string | null;
  status: string;
  vote_count: number;
  vote_stats: VoteStats | null;
}

export interface GroupDetail extends ParliamentaryGroup {
  member_count: number;
  vote_count: number;
  vote_stats: VoteStats | null;
  members: GroupMember[];
}

export interface PartyDetail {
  party: string;
  candidate_count: number;
  vote_count: number;
  vote_stats: VoteStats | null;
  candidates: Candidate[];
}

export interface IngestionRun {
  id: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  stats: Record<string, number>;
  errors: string[];
}

export interface AppStats {
  candidate_count: number;
  database: string;
  last_ingestion_at: string | null;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, init);
  if (!res.ok) {
    let detail = `API error: ${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) {
        detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      // ignore non-JSON error bodies
    }
    throw new Error(detail);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json();
}

function withSecret(secret: string, init: RequestInit = {}): RequestInit {
  const headers = new Headers(init.headers);
  headers.set('X-Ingestion-Secret', secret);
  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  return { ...init, headers };
}

export type CandidateStatus = 'declared' | 'potential' | 'withdrawn';

export interface CandidateCreateInput {
  full_name: string;
  party?: string | null;
  status?: CandidateStatus;
  slug?: string | null;
  clair_slug?: string | null;
}

export interface CandidateUpdateInput {
  party?: string | null;
  status?: CandidateStatus;
  clair_slug?: string | null;
}

/** Partis connus (seed + usage courant) — le champ reste libre via « Autre… ». */
export const KNOWN_PARTIES = [
  'RE',
  'RN',
  'LFI',
  'LR',
  'PS',
  'EELV',
  'PCF',
  'Place publique',
  'MoDem',
  'Horizons',
] as const;

export const CHAMBER_LABELS: Record<string, string> = {
  assemblee: 'Assemblée nationale',
  senat: 'Sénat',
  parlement_europeen: 'Parlement européen',
};

export function clairScrutinUrl(vote: Pick<ParliamentaryVote, 'scrutin_id' | 'source' | 'chamber'>) {
  const raw = vote.source?.url || '';
  // Corrige les anciennes URLs stockées avec l'UUID CLAIR au lieu du numéro public.
  if (/clair\.vote\/scrutins\/[0-9a-f-]{20,}/i.test(raw) && vote.scrutin_id) {
    return `https://clair.vote/scrutins/${vote.scrutin_id}`;
  }
  if (raw.includes('clair.vote')) return raw;
  if (vote.scrutin_id && (vote.chamber === 'assemblee' || vote.chamber === 'senat')) {
    return `https://clair.vote/scrutins/${vote.scrutin_id}`;
  }
  return raw;
}

export function clairDeputeUrl(clairSlug: string | undefined | null) {
  if (!clairSlug) return null;
  return `https://clair.vote/deputes/${clairSlug}`;
}

export const api = {
  health: () => fetchJson<{ status: string; database: string }>('/health'),
  stats: () => fetchJson<AppStats>('/stats'),
  candidates: () => fetchJson<Candidate[]>('/candidates'),
  candidate: (slug: string) => fetchJson<CandidateDetail>(`/candidates/${slug}`),
  createCandidate: (secret: string, payload: CandidateCreateInput) =>
    fetchJson<Candidate>('/candidates', withSecret(secret, {
      method: 'POST',
      body: JSON.stringify(payload),
    })),
  updateCandidate: (secret: string, slug: string, payload: CandidateUpdateInput) =>
    fetchJson<Candidate>(`/candidates/${slug}`, withSecret(secret, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })),
  deleteCandidate: (secret: string, slug: string) =>
    fetchJson<void>(`/candidates/${slug}`, withSecret(secret, { method: 'DELETE' })),
  interviews: (slug: string, page = 1) =>
    fetchJson<Paginated<Interview>>(`/candidates/${slug}/interviews?page=${page}`),
  programs: (slug: string, page = 1) =>
    fetchJson<Paginated<ProgramDocument>>(`/candidates/${slug}/programs?page=${page}`),
  votes: (slug: string, page = 1, chamber?: string) => {
    const params = new URLSearchParams({ page: String(page), page_size: '100' });
    if (chamber) params.set('chamber', chamber);
    return fetchJson<Paginated<ParliamentaryVote>>(
      `/candidates/${slug}/votes?${params.toString()}`,
    );
  },
  articles: (slug: string, page = 1) =>
    fetchJson<Paginated<Article>>(`/candidates/${slug}/articles?page=${page}`),
  topics: () => fetchJson<Topic[]>('/topics'),
  claims: (slug: string) => fetchJson<Claim[]>(`/candidates/${slug}/claims`),
  createClaim: (secret: string, slug: string, payload: ClaimCreateInput) =>
    fetchJson<Claim>(`/candidates/${slug}/claims`, withSecret(secret, {
      method: 'POST',
      body: JSON.stringify(payload),
    })),
  deleteClaim: (secret: string, claimId: string) =>
    fetchJson<void>(`/claims/${claimId}`, withSecret(secret, { method: 'DELETE' })),
  coherence: (slug: string) =>
    fetchJson<CandidateCoherence>(`/candidates/${slug}/coherence`),
  setVoteTopics: (secret: string, voteId: string, topicSlugs: string[]) =>
    fetchJson<Topic[]>(`/votes/${voteId}/topics`, withSecret(secret, {
      method: 'PUT',
      body: JSON.stringify({ topic_slugs: topicSlugs }),
    })),
  classifyVoteTopics: (
    secret: string,
    slug: string,
    opts?: { only_untagged?: boolean; limit?: number },
  ) => {
    const params = new URLSearchParams();
    if (opts?.only_untagged !== undefined) {
      params.set('only_untagged', String(opts.only_untagged));
    }
    if (opts?.limit !== undefined) params.set('limit', String(opts.limit));
    const qs = params.toString();
    return fetchJson<LlmClassifyVotesResult>(
      `/candidates/${slug}/votes/classify-topics${qs ? `?${qs}` : ''}`,
      withSecret(secret, { method: 'POST' }),
    );
  },
  extractProgramClaims: (
    secret: string,
    slug: string,
    opts?: { limit_programs?: number; max_claims_per_program?: number },
  ) => {
    const params = new URLSearchParams();
    if (opts?.limit_programs !== undefined) {
      params.set('limit_programs', String(opts.limit_programs));
    }
    if (opts?.max_claims_per_program !== undefined) {
      params.set('max_claims_per_program', String(opts.max_claims_per_program));
    }
    const qs = params.toString();
    return fetchJson<LlmExtractClaimsResult>(
      `/candidates/${slug}/programs/extract-claims${qs ? `?${qs}` : ''}`,
      withSecret(secret, { method: 'POST' }),
    );
  },
  groups: () => fetchJson<GroupDetail[]>('/groups'),
  group: (slug: string) => fetchJson<GroupDetail>(`/groups/${slug}`),
  parties: () => fetchJson<PartyDetail[]>('/parties'),
  party: (party: string) => fetchJson<PartyDetail>(`/parties/${encodeURIComponent(party)}`),
  ingestionRuns: () => fetchJson<IngestionRun[]>('/ingestion/runs'),
};

export const COHERENCE_LABELS: Record<CoherenceStatus, string> = {
  aligned: 'Aligné',
  conflict: 'Contradiction',
  mixed: 'Mixte',
  abstention_only: 'Sans polarité claire',
  claims_only: 'Déclaration seule',
  votes_only: 'Vote seul',
  empty: 'Vide',
};

export const STANCE_LABELS: Record<ClaimStance, string> = {
  pour: 'Pour',
  contre: 'Contre',
  nuance: 'Nuancé',
  inconnu: 'Inconnu',
};

export function formatLoyalty(rate: number | null | undefined): string {
  if (rate == null) return '—';
  return `${Math.round(rate * 100)} %`;
}
