import type {
  ActivityEntry,
  CheckItem,
  Comment,
  Project,
  ProjectGroup,
  Section,
  Tag,
  Task,
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

export const tagsApi = {
  list: () => http.get<Tag[]>('/api/tags/'),
  create: (data: Partial<Tag>) => http.post<Tag>('/api/tags/', data),
  update: (id: number, data: Partial<Tag>) => http.patch<Tag>(`/api/tags/${id}/`, data),
  remove: (id: number) => http.delete(`/api/tags/${id}/`),
  merge: (id: number, target: number) => http.post<Tag>(`/api/tags/${id}/merge/`, { target }),
}
