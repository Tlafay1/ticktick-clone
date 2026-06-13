import { describe, expect, it } from 'vitest'
import { parseQuickAdd } from '../nlp'
import { PRIORITY } from '@/types'

const ref = new Date(2026, 5, 12, 9, 0) // vendredi 12 juin 2026

describe('parseQuickAdd', () => {
  it('extrait date et heure : "Lunch tomorrow at 1pm"', () => {
    const p = parseQuickAdd('Lunch tomorrow at 1pm', { reference: ref })
    expect(p.title).toBe('Lunch')
    expect(p.due?.getDate()).toBe(13)
    expect(p.due?.getHours()).toBe(13)
    expect(p.hasTime).toBe(true)
  })

  it('date sans heure → all day', () => {
    const p = parseQuickAdd('Rapport next monday', { reference: ref })
    expect(p.hasTime).toBe(false)
    expect(p.due?.getDay()).toBe(1)
  })

  it('priorité par mot-clé !high', () => {
    const p = parseQuickAdd('Payer impôts !high', { reference: ref })
    expect(p.priority).toBe(PRIORITY.HIGH)
    expect(p.title).toBe('Payer impôts')
  })

  it('priorité par !!! et !!', () => {
    expect(parseQuickAdd('x !!!').priority).toBe(PRIORITY.HIGH)
    expect(parseQuickAdd('x !!').priority).toBe(PRIORITY.MEDIUM)
    expect(parseQuickAdd('x !').priority).toBe(PRIORITY.LOW)
  })

  it("un ! au milieu d'un mot n'est pas une priorité", () => {
    const p = parseQuickAdd('Wow! grande nouvelle')
    expect(p.priority).toBeNull()
  })

  it('tags #marketing et hiérarchie #Work/Finance', () => {
    const p = parseQuickAdd('Préparer campagne #marketing #Work/Finance')
    expect(p.tagNames).toEqual(['marketing', 'Work/Finance'])
    expect(p.title).toBe('Préparer campagne')
  })

  it('liste via ^Work', () => {
    const p = parseQuickAdd('Réunion équipe ^Work', { projectNames: ['Work'] })
    expect(p.projectName).toBe('Work')
    expect(p.title).toBe('Réunion équipe')
  })

  it('liste multi-mots via ~ avec correspondance', () => {
    const p = parseQuickAdd('Tâche ~Side Projects', {
      projectNames: ['Side Projects'],
    })
    expect(p.projectName).toBe('Side Projects')
  })

  it('option strip désactivée : le titre reste intact', () => {
    const p = parseQuickAdd('Lunch tomorrow !high #food', {
      strip: false,
      reference: ref,
    })
    expect(p.title).toBe('Lunch tomorrow !high #food')
    expect(p.priority).toBe(PRIORITY.HIGH)
    expect(p.due).not.toBeNull()
  })

  it('combinaison complète', () => {
    const p = parseQuickAdd('Buy milk tomorrow 3pm !high #courses ^Inbox', {
      reference: ref,
      projectNames: ['Inbox'],
    })
    expect(p.title).toBe('Buy milk')
    expect(p.due?.getHours()).toBe(15)
    expect(p.priority).toBe(PRIORITY.HIGH)
    expect(p.tagNames).toEqual(['courses'])
    expect(p.projectName).toBe('Inbox')
  })
})
