const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api';

export type QuestStatus = 'locked' | 'available' | 'active' | 'completed';

export interface Trader {
  id:          number;
  slug:        string;
  name:        string;
  description: string;
  image:       string | null;
  available:   boolean;
  reputation:  string;
}

export interface PlayerProfile {
  nickname:             string;
  avatar:               string | null;
  rubles:               number;
  euros:                number;
  dollars:              number;
  experience:           number;
  experience_per_level: number;
  level:                number;
}

export function getPlayerProfile() {
  return apiRequest<PlayerProfile>('/player/');
}

export interface QuestProgress {
  completed: number;
  total:     number;
}

export interface QuestListItem {
  image:             string | null;
  id:                number;
  slug:              string;
  title:             string;
  description:       string;
  status:            QuestStatus;
  trader:            Pick<Trader, 'id' | 'slug' | 'name'>;
  progress:          QuestProgress;
  sort_order:        number;
  reputation_reward: string;
  rubles_reward:     number;
  euros_reward:      number;
  dollars_reward:    number;
  experience_reward: number;
}

export interface QuestObjective {
  latest_submission: Submission | null;
  id:                number;
  type:              string;
  title:             string;
  description:       string;
  required_amount:   number;
  current_amount:    number;
  completed:         boolean;
  completed_at:      string | null;
  sort_order:        number;
  metadata:          Record<string, unknown>;
  item:              unknown | null;
  location:          unknown | null;
}

export interface QuestDetail extends QuestListItem {
  objectives:   QuestObjective[];
  requirements: Array<{
    id:     number;
    slug:   string;
    title:  string;
    status: QuestStatus;
  }>;
}

export interface ProgressSummary {
  quests: {
    total:     number;
    completed: number;
    active:    number;
    available: number;
    locked:    number;
  };
  objectives: {
    total:     number;
    completed: number;
  };
}

export interface SubmissionPayload {
  amount:   number;
  comment?: string;
  proof?:   string;
}

export interface Submission {
  id:            number;
  objective:     number;
  amount:        number;
  status:        'pending' | 'approved' | 'rejected';
  admin_comment: string;
  reviewed_at:   string | null;
}

interface QuestListParams {
  trader?: string | null;
  status?: QuestStatus;
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
    ...init,
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function getTraders() {
  return apiRequest<Trader[]>('/traders/');
}

export function getQuests(params: QuestListParams = {}) {
  const searchParams = new URLSearchParams();

  if (params.trader) {
    searchParams.set('trader', params.trader);
  }

  if (params.status) {
    searchParams.set('status', params.status);
  }

  const queryString = searchParams.toString();

  return apiRequest<QuestListItem[]>(`/quests/${queryString ? `?${queryString}` : ''}`);
}

export function getQuest(id: number) {
  return apiRequest<QuestDetail>(`/quests/${id}/`);
}

export function getProgress() {
  return apiRequest<ProgressSummary>('/progress/');
}

export function startQuest(id: number) {
  return apiRequest<QuestDetail>(`/quests/${id}/start/`, {
    method: 'POST',
  });
}

export function submitObjective(id: number, payload: SubmissionPayload) {
  return apiRequest<Submission>(`/objectives/${id}/submit/`, {
    method: 'POST',
    body:   JSON.stringify(payload),
  });
}

export function completeQuest(id: number) {
  return apiRequest<QuestDetail>(`/quests/${id}/complete/`, {
    method: 'POST',
  });
}
