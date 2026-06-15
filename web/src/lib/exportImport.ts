import type { Task } from '@/types'

// ── Export CSV ──────────────────────────────────────────────────────────────

function escapeCsv(v: unknown): string {
  const s = v == null ? '' : String(v)
  return s.includes(',') || s.includes('"') || s.includes('\n')
    ? `"${s.replace(/"/g, '""')}"`
    : s
}

const CSV_HEADERS = [
  'id', 'title', 'description', 'status', 'priority',
  'due_date', 'start_date', 'is_all_day', 'project', 'section',
  'parent', 'tags', 'rrule', 'progress', 'is_pinned', 'created_at',
]

export function tasksToCSV(tasks: Task[]): string {
  const rows = tasks.map(t =>
    CSV_HEADERS.map(h => {
      const v = (t as unknown as Record<string, unknown>)[h]
      return escapeCsv(Array.isArray(v) ? v.join('|') : v)
    }).join(',')
  )
  return [CSV_HEADERS.join(','), ...rows].join('\n')
}

export function tasksToJSON(tasks: Task[]): string {
  return JSON.stringify(tasks, null, 2)
}

export function downloadFile(content: string, filename: string, mime: string) {
  const blob = new Blob([content], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

// ── Import CSV ──────────────────────────────────────────────────────────────

function parseCsvRow(row: string): string[] {
  const result: string[] = []
  let inQuote = false
  let cur = ''
  for (let i = 0; i < row.length; i++) {
    const c = row[i]
    if (c === '"') {
      if (inQuote && row[i + 1] === '"') { cur += '"'; i++ }
      else inQuote = !inQuote
    } else if (c === ',' && !inQuote) {
      result.push(cur); cur = ''
    } else {
      cur += c
    }
  }
  result.push(cur)
  return result
}

export interface ImportedTask {
  title: string
  description?: string
  status?: number
  priority?: number
  due_date?: string
  project_name?: string
}

export function parseCSV(text: string): ImportedTask[] {
  const lines = text.split('\n').filter(l => l.trim())
  if (lines.length < 2) return []
  const headers = parseCsvRow(lines[0]).map(h => h.trim())
  return lines.slice(1).map(line => {
    const vals = parseCsvRow(line)
    const row: Record<string, string> = {}
    headers.forEach((h, i) => { row[h] = vals[i] ?? '' })
    return {
      title: row.title ?? row.Title ?? row.name ?? '',
      description: row.description ?? row.Description ?? '',
      status: row.status ? Number(row.status) : 0,
      priority: row.priority ? Number(row.priority) : 0,
      due_date: row.due_date || row.due || undefined,
      project_name: row.project_name ?? row.list ?? undefined,
    }
  }).filter(t => t.title.trim())
}

export function parseJSON(text: string): ImportedTask[] {
  try {
    const data = JSON.parse(text)
    if (!Array.isArray(data)) return []
    return data.filter(t => typeof t.title === 'string' && t.title.trim())
  } catch {
    return []
  }
}
