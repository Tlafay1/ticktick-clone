import type {
  ActivityEntry,
  Attachment,
  CheckItem,
  Comment,
  Countdown,
  FocusSession,
  Habit,
  HabitCheckIn,
  ProductivityScore,
  Project,
  ProjectGroup,
  Reminder,
  Section,
  StatsSummary,
  Tag,
  Task,
  TaskVersion,
  Template,
  User,
  UserSettings,
} from '@/types'
import { http, qs, tokens } from './client'

export const authApi = {
  async register(email: string, password: string, displayName = '') {
    const data = await http.post<{ user: User; access: string; refresh: string }>(
      '/api/auth/register/',
      { email, password, display_name: displayName },
    )
    tokens.set(data.access, data.refresh)
    return data.user
  },
  async login(email: string, password: string) {
    const data = await http.post<{ access: string; refresh: string }>(
      '/api/auth/token/',
      { email, password },
    )
    tokens.set(data.access, data.refresh)
  },
  logout: () => tokens.clear(),
  me: () => http.get<User>('/api/me/'),
  updateSettings: (patch: Partial<UserSettings>) =>
    http.patch<UserSettings>('/api/me/settings/', patch),
}

export const projectsApi = {
  list: () => http.get<Project[]>('/api/projects/'),
  create: (data: Partial<Project>) => http.post<Project>('/api/projects/', data),
  update: (id: number, data: Partial<Project>) =>
    http.patch<Project>(`/api/projects/${id}/`, data),
  remove: (id: number) => http.delete(`/api/projects/${id}/`),
  groups: () => http.get<ProjectGroup[]>('/api/project-groups/'),
  createGroup: (data: Partial<ProjectGroup>) =>
    http.post<ProjectGroup>('/api/project-groups/', data),
  updateGroup: (id: number, data: Partial<ProjectGroup>) =>
    http.patch<ProjectGroup>(`/api/project-groups/${id}/`, data),
  removeGroup: (id: number) => http.delete(`/api/project-groups/${id}/`),
  createSection: (data: Partial<Section>) => http.post<Section>('/api/sections/', data),
  updateSection: (id: number, data: Partial<Section>) => http.patch<Section>(`/api/sections/${id}/`, data),
  removeSection: (id: number) => http.delete(`/api/sections/${id}/`),
}

export type TaskQuery = Record<string, string | number | boolean | undefined>

export const tasksApi = {
  list: (params: TaskQuery = {}) => http.get<Task[]>(`/api/tasks/${qs(params)}`),
  get: (id: number) => http.get<Task>(`/api/tasks/${id}/`),
  create: (data: Partial<Task>) => http.post<Task>('/api/tasks/', data),
  update: (id: number, data: Partial<Task>) => http.patch<Task>(`/api/tasks/${id}/`, data),
  remove: (id: number, permanent = false) =>
    http.delete(`/api/tasks/${id}/${permanent ? '?permanent=1' : ''}`),
  complete: (id: number) => http.post<Task>(`/api/tasks/${id}/complete/`),
  wontDo: (id: number) => http.post<Task>(`/api/tasks/${id}/wont-do/`),
  reopen: (id: number) => http.post<Task>(`/api/tasks/${id}/reopen/`),
  restore: (id: number) => http.post<Task>(`/api/tasks/${id}/restore/`),
  duplicate: (id: number) => http.post<Task>(`/api/tasks/${id}/duplicate/`),
  emptyTrash: () => http.post('/api/tasks/empty-trash/'),
  activity: (id: number) => http.get<ActivityEntry[]>(`/api/tasks/${id}/activity/`),
  importFile: async (file: File, dedupe = false) => {
    const fd = new FormData()
    fd.append('file', file)
    const res = await fetch(`/api/tasks/import/${dedupe ? '?dedupe=1' : ''}`, {
      method: 'POST',
      headers: tokens.access ? { Authorization: `Bearer ${tokens.access}` } : {},
      body: fd,
    })
    if (!res.ok) throw new Error('Échec de l\'import')
    return res.json() as Promise<{ imported: number; folders_created: number; projects_created: number; tags_created: number; skipped: number }>
  },
}

export const checkItemsApi = {
  create: (data: Partial<CheckItem>) => http.post<CheckItem>('/api/check-items/', data),
  update: (id: number, data: Partial<CheckItem>) =>
    http.patch<CheckItem>(`/api/check-items/${id}/`, data),
  remove: (id: number) => http.delete(`/api/check-items/${id}/`),
}

export const commentsApi = {
  list: (taskId: number) => http.get<Comment[]>(`/api/comments/?task=${taskId}`),
  create: (taskId: number, content: string) =>
    http.post<Comment>('/api/comments/', { task: taskId, content }),
  update: (id: number, content: string) =>
    http.patch<Comment>(`/api/comments/${id}/`, { content }),
  remove: (id: number) => http.delete(`/api/comments/${id}/`),
}

export const remindersApi = {
  list: (taskId: number) => http.get<Reminder[]>(`/api/reminders/?task=${taskId}`),
  create: (data: Partial<Reminder>) => http.post<Reminder>('/api/reminders/', data),
  remove: (id: number) => http.delete(`/api/reminders/${id}/`),
}

export const tagsApi = {
  list: () => http.get<Tag[]>('/api/tags/'),
  create: (data: Partial<Tag>) => http.post<Tag>('/api/tags/', data),
  update: (id: number, data: Partial<Tag>) => http.patch<Tag>(`/api/tags/${id}/`, data),
  remove: (id: number) => http.delete(`/api/tags/${id}/`),
  merge: (id: number, target: number) => http.post<Tag>(`/api/tags/${id}/merge/`, { target }),
}

export const habitsApi = {
  list: () => http.get<Habit[]>('/api/habits/'),
  create: (data: Partial<Habit>) => http.post<Habit>('/api/habits/', data),
  update: (id: number, data: Partial<Habit>) => http.patch<Habit>(`/api/habits/${id}/`, data),
  remove: (id: number) => http.delete(`/api/habits/${id}/`),
  checkIn: (id: number, data: { date: string; quantity?: number; note?: string }) =>
    http.post<HabitCheckIn>(`/api/habits/${id}/checkins/`, data),
  checkIns: (id: number) => http.get<HabitCheckIn[]>(`/api/habits/${id}/checkins/`),
  presets: () => http.get<Partial<Habit>[]>('/api/habits/presets/'),
}

export const focusApi = {
  list: () => http.get<FocusSession[]>('/api/focus-sessions/'),
  create: (data: Partial<FocusSession>) => http.post<FocusSession>('/api/focus-sessions/', data),
  update: (id: number, data: Partial<FocusSession>) => http.patch<FocusSession>(`/api/focus-sessions/${id}/`, data),
  stats: () => http.get<{ total_seconds: number; by_list: unknown[]; by_tag: unknown[] }>('/api/focus-sessions/stats/'),
}

export const countdownApi = {
  list: () => http.get<Countdown[]>('/api/countdowns/'),
  create: (data: Partial<Countdown>) => http.post<Countdown>('/api/countdowns/', data),
  update: (id: number, data: Partial<Countdown>) => http.patch<Countdown>(`/api/countdowns/${id}/`, data),
  remove: (id: number) => http.delete(`/api/countdowns/${id}/`),
}

export const attachmentsApi = {
  list: (taskId: number) => http.get<Attachment[]>(`/api/attachments/?task=${taskId}`),
  upload: async (taskId: number, file: File): Promise<Attachment> => {
    const fd = new FormData()
    fd.append('task', String(taskId))
    fd.append('file', file)
    const res = await fetch('/api/attachments/', {
      method: 'POST',
      headers: tokens.access ? { Authorization: `Bearer ${tokens.access}` } : {},
      body: fd,
    })
    if (!res.ok) throw new Error('Upload failed')
    return res.json()
  },
  remove: (id: number) => http.delete(`/api/attachments/${id}/`),
}

export const versionsApi = {
  list: (taskId: number) => http.get<TaskVersion[]>(`/api/tasks/${taskId}/versions/`),
  restore: (taskId: number, versionId: number) =>
    // Contrat backend : action « restore-version » avec version_id en body.
    http.post<Task>(`/api/tasks/${taskId}/restore-version/`, { version_id: versionId }),
}

export const statsApi = {
  summary: () => http.get<StatsSummary>('/api/stats/summary/'),
  heatmap: () => http.get<Array<{ date: string; count: number }>>('/api/stats/heatmap/'),
  monthly: () => http.get<Array<{ month: string; count: number }>>('/api/stats/monthly/'),
  score: () => http.get<ProductivityScore>('/api/stats/productivity-score/'),
}

export const templatesApi = {
  list: () => http.get<Template[]>('/api/templates/'),
  get: (id: number) => http.get<Template>(`/api/templates/${id}/`),
  create: (data: { name: string; scope: 'task' | 'project'; data: object }) =>
    http.post<Template>('/api/templates/', data),
  update: (id: number, data: Partial<Template>) =>
    http.patch<Template>(`/api/templates/${id}/`, data),
  remove: (id: number) => http.delete(`/api/templates/${id}/`),
}

export interface ApiKeyInfo {
  id: number
  key: string
  label: string
  created_at: string
  last_used_at: string | null
}

export const apiKeysApi = {
  list: () => http.get<ApiKeyInfo[]>('/api/api-keys/'),
  create: (label = '') => http.post<ApiKeyInfo>('/api/api-keys/', { label }),
  remove: (id: number) => http.delete(`/api/api-keys/${id}/`),
}

export interface Webhook {
  id: number
  url: string
  events: string[]
  secret: string
  is_active: boolean
  created_at: string
  last_triggered_at: string | null
}

export const webhooksApi = {
  list: () => http.get<Webhook[]>('/api/webhooks/'),
  events: () => http.get<{ events: string[] }>('/api/webhooks/events/'),
  create: (url: string, events: string[]) =>
    http.post<Webhook>('/api/webhooks/', { url, events }),
  update: (id: number, data: Partial<Webhook>) =>
    http.patch<Webhook>(`/api/webhooks/${id}/`, data),
  remove: (id: number) => http.delete(`/api/webhooks/${id}/`),
  ping: (id: number) => http.post<{ detail: string }>(`/api/webhooks/${id}/ping/`, {}),
}
