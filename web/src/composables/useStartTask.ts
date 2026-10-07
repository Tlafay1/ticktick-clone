// « Juste commencer » : 10 minutes sur une tâche, en un geste. Si un créneau
// est ouvert à ce moment, c'est lui qu'on honore (la tâche devient sa prochaine
// action) ; sinon une simple session focus de 10 min.
import type { Router } from 'vue-router'
import { focusApi, methodApi, occurrencesApi } from '@/api'
import { ApiError } from '@/api/client'
import { canStart } from '@/lib/method'

const CONTRACT_SECONDS = 600

export async function startTenMinutes(taskId: number, router: Router): Promise<void> {
  const today = await methodApi.today().catch(() => null)
  const open = today?.occurrences.find(o => o.kind === 'work' && canStart(o))
  try {
    if (open) await occurrencesApi.start(open.id, { task: taskId })
    else await focusApi.start({ task: taskId, planned_seconds: CONTRACT_SECONDS })
  } catch (e) {
    // Une session tourne déjà : on l'affiche plutôt que d'en lancer une seconde.
    if (!(e instanceof ApiError && e.status === 409)) throw e
  }
  router.push('/focus')
}
