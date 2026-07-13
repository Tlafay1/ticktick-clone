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
  daily_review_morning: string | null
  daily_review_evening: string | null
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
  is_done: boolean
}

export interface FilterRule {
  type: 'and' | 'or'
  rules: Array<{
    field: 'priority' | 'status' | 'due' | 'tag' | 'project' | 'assignee'
    op: 'eq' | 'neq' | 'lt' | 'gt' | 'in' | 'not_in' | 'is_null' | 'is_not_null'
    value?: unknown
  }>
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
  is_smart: boolean
  filter_rules: FilterRule[]
  sections: Section[]
  bg_color: string
  bg_image_url: string
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
  planned_date: string | null
  end_date: string | null
  is_all_day: boolean
  timezone_name: string
  rrule: string
  repeat_from: 'due' | 'completion'
  tags: number[]
  sort_order: number
  estimated_pomos: number
  completed_at: string | null
  trashed_at: string | null
  archived_at: string | null
  created_at: string
  modified_at: string
  check_items: CheckItem[]
  reminders: NestedReminder[]
}

/** Rappel imbriqué dans TaskSerializer (sans FK task). */
export interface NestedReminder {
  id: number
  trigger_type: 'relative' | 'absolute'
  minutes_before: number | null
  trigger_at: string | null
  annoying: boolean
}

export interface Reminder {
  id: number
  task: number
  trigger_type: 'relative' | 'absolute'
  minutes_before: number | null
  trigger_at: string | null
  annoying: boolean
}

export interface Comment {
  id: number
  task: number
  content: string
  created_at: string
  edited_at: string | null
}

export interface Habit {
  id: number
  name: string
  icon: string
  color: string
  frequency: 'daily' | 'weekly' | 'specific_days' | 'interval' | 'weekly_goal'
  freq_config: Record<string, unknown>
  goal_type: 'binary' | 'numeric'
  goal_value: number
  goal_unit: string
  motto: string
  check_in_mode: 'auto' | 'manual' | 'binary'
  auto_increment: boolean
  sort_order: number
  archived: boolean
  created_at: string
  reminders: Array<{ id: number; time: string }>
  streak: number
  max_streak: number
}

export interface HabitCheckIn {
  id: number
  date: string
  quantity: number
  note: string
  completed: boolean
  created_at: string
}

export interface FocusSession {
  id: number
  task: number | null
  mode: 'pomodoro' | 'stopwatch'
  session_type: 'work' | 'short_break' | 'long_break'
  start_at: string
  end_at: string | null
  duration_seconds: number
}

export interface Countdown {
  id: number
  title: string
  target_date: string
  description: string
  pinned: boolean
  created_at: string
  days_remaining: number
}

export interface StatsSummary {
  completed_today: number
  overdue: number
  by_list: Array<{ project__name: string; count: number }>
  best_hours: Array<{ hour: number; count: number }>
}

export interface ProductivityScore {
  score: number
  level: string
  on_time: number
  late: number
}

export interface Attachment {
  id: number
  task: number
  filename: string
  content_type: string
  size: number
  url: string
  created_at: string
}

export interface TaskVersion {
  id: number
  task: number
  description: string
  created_at: string
}

export interface ActivityEntry {
  id: number
  action: string
  payload: Record<string, unknown>
  created_at: string
}

export interface Template {
  id: number
  scope: 'task' | 'project'
  name: string
  data: Partial<Task> | Partial<Project>
}
