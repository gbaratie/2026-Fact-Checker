const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface Source {
  id: string;
  source_type: string;
  url: string;
  publisher: string | null;
  fetched_at: string;
  raw_metadata?: Record<string, string | number | null>;
}

export interface Candidate {
  id: string;
  slug: string;
  full_name: string;
  party: string | null;
  external_ids: Record<string, string>;
  status: string;
}

export interface CandidateDetail extends Candidate {
  interview_count: number;
  program_count: number;
  vote_count: number;
  article_count: number;
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
  vote_date: string | null;
  source: Source;
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

export interface IngestionRun {
  id: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  stats: Record<string, number>;
  errors: string[];
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const api = {
  health: () => fetchJson<{ status: string; database: string }>('/health'),
  candidates: () => fetchJson<Candidate[]>('/candidates'),
  candidate: (slug: string) => fetchJson<CandidateDetail>(`/candidates/${slug}`),
  interviews: (slug: string, page = 1) =>
    fetchJson<Paginated<Interview>>(`/candidates/${slug}/interviews?page=${page}`),
  programs: (slug: string, page = 1) =>
    fetchJson<Paginated<ProgramDocument>>(`/candidates/${slug}/programs?page=${page}`),
  votes: (slug: string, page = 1) =>
    fetchJson<Paginated<ParliamentaryVote>>(`/candidates/${slug}/votes?page=${page}`),
  articles: (slug: string, page = 1) =>
    fetchJson<Paginated<Article>>(`/candidates/${slug}/articles?page=${page}`),
  ingestionRuns: () => fetchJson<IngestionRun[]>('/ingestion/runs'),
};
