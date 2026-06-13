export interface UserSettings {
  theme: 'auto' | 'light' | 'dark'
  theme_preset: string
  week_start: number
  reminder_sound: string
  smart_list_visibility: Record<string, boolean>
  default_project: number | null
  default_due: 'none' | 'today' | 'tomorrow'
  default_priority: number
  default_reminders: unknown[]
  snooze_options: unknown[]
  nlp_enabled: boolean
  nlp_strip_text: boolean
}

export interface User {
  id: number
  email: string
  display_name: string
  date_joined: string
  settings: UserSettings
}

export interface ProjectGroup {
  id: number
  name: string
  sort_order: number
  collapsed: boolean
}

export interface Section {
  id: number
  project: number
  name: string
  sort_order: number
  collapsed: boolean
}

export interface Project {
  id: number
  group: number | null
  name: string
  color: string
  icon: string
  view_mode: 'list' | 'kanban' | 'timeline'
  sort_order: number
  is_inbox: boolean
  archived: boolean
  hidden_from_smart_lists: boolean
  sections: Section[]
}

export interface Tag {
  id: number
  name: string
  color: string
  parent: number | null
  sort_order: number
}

export interface CheckItem {
  id: number
  task: number
  title: string
  is_done: boolean
  completed_at: string | null
  sort_order: number
}

export const STATUS = { NORMAL: 0, COMPLETED: 2, WONT_DO: -1 } as const
export const PRIORITY = { NONE: 0, LOW: 1, MEDIUM: 3, HIGH: 5 } as const

export interface Task {
  id: number
  project: number
  section: number | null
  parent: number | null
  title: string
  description: string
  status: number
  priority: number
  progress: number
  is_pinned: boolean
  pinned_at: string | null
  start_date: string | null
  due_date: string | null
  is_all_day: boolean
  timezone_name: string
  rrule: string
  repeat_from: 'due' | 'completion'
  tags: number[]
  sort_order: number
  completed_at: string | null
  trashed_at: string | null
  created_at: string
  modified_at: string
  check_items: CheckItem[]
}

export interface Comment {
  id: number
  task: number
  content: string
  created_at: string
  edited_at: string | null
}

export interface ActivityEntry {
  id: number
  action: string
  payload: Record<string, unknown>
  created_at: string
}
