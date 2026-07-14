import { describe, it, expect } from 'vitest'
import { tasksToCSV, tasksToJSON, parseCSV, parseJSON } from '../exportImport'
import type { Task } from '@/types'

const TASK: Task = {
  id: 1, project: 1, section: null, parent: null,
  title: 'Acheter du pain', description: '', status: 0, priority: 3,
  progress: 0, is_pinned: false, pinned_at: null,
  start_date: null, due_date: '2026-06-15T00:00:00Z', planned_date: null, end_date: null,
  is_all_day: true,
  timezone_name: 'Europe/Paris', rrule: '', repeat_from: 'due',
  tags: [1, 2], sort_order: 1000, estimated_pomos: 0, completed_at: null, trashed_at: null,
  archived_at: null,
  created_at: '2026-06-01T00:00:00Z', modified_at: '2026-06-01T00:00:00Z',
  check_items: [], reminders: [], last_actor: 'user', claimed_by: null,
}

describe('tasksToCSV', () => {
  it('produit une ligne par tâche avec en-têtes', () => {
    const csv = tasksToCSV([TASK])
    const lines = csv.split('\n')
    expect(lines.length).toBe(2)
    expect(lines[0]).toContain('title')
    expect(lines[1]).toContain('Acheter du pain')
  })

  it('échappe les virgules et guillemets', () => {
    const t = { ...TASK, title: 'Foo, "bar"' }
    const csv = tasksToCSV([t])
    expect(csv).toContain('"Foo, ""bar"""')
  })

  it('joint les tableaux (tags) avec |', () => {
    const csv = tasksToCSV([TASK])
    expect(csv).toContain('1|2')
  })
})

describe('tasksToJSON', () => {
  it('produit un JSON valide', () => {
    const json = tasksToJSON([TASK])
    const parsed = JSON.parse(json)
    expect(Array.isArray(parsed)).toBe(true)
    expect(parsed[0].title).toBe('Acheter du pain')
  })
})

describe('parseCSV', () => {
  it('parse un CSV simple', () => {
    const csv = 'title,priority,due_date\nAcheter du pain,3,2026-06-15'
    const tasks = parseCSV(csv)
    expect(tasks).toHaveLength(1)
    expect(tasks[0].title).toBe('Acheter du pain')
    expect(tasks[0].priority).toBe(3)
    expect(tasks[0].due_date).toBe('2026-06-15')
  })

  it('ignore les lignes vides', () => {
    const csv = 'title\nFoo\n\n\nBar'
    expect(parseCSV(csv)).toHaveLength(2)
  })

  it('filtre les lignes sans titre', () => {
    const csv = 'title,priority\n,3\nBon titre,0'
    expect(parseCSV(csv)).toHaveLength(1)
  })

  it('accepte les champs Todoist (Title)', () => {
    const csv = 'Title\nFaire quelque chose'
    const tasks = parseCSV(csv)
    expect(tasks[0].title).toBe('Faire quelque chose')
  })
})

describe('parseJSON', () => {
  it('parse un tableau JSON de tâches', () => {
    const json = JSON.stringify([{ title: 'Test', priority: 5 }])
    const tasks = parseJSON(json)
    expect(tasks).toHaveLength(1)
    expect(tasks[0].title).toBe('Test')
    expect(tasks[0].priority).toBe(5)
  })

  it('retourne [] sur JSON invalide', () => {
    expect(parseJSON('not json')).toEqual([])
  })

  it('retourne [] si pas un tableau', () => {
    expect(parseJSON('{"title":"x"}')).toEqual([])
  })
})
