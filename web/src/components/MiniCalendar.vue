<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import {
  startOfMonth, endOfMonth, startOfWeek, endOfWeek,
  eachDayOfInterval, addMonths, format, isToday, isSameMonth, isSameDay,
} from 'date-fns'
import { fr } from 'date-fns/locale'

// Mini-calendrier mensuel en bas de sidebar (comme TickTick desktop).
// Cliquer un jour ouvre le calendrier centré sur cette date.
const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const pivot = ref(new Date())

const weekStartsOn = computed<0 | 1 | 6>(() => {
  const v = userStore.user?.settings?.week_start ?? 1
  return (v === 0 || v === 6 ? v : 1)
})

const days = computed(() =>
  eachDayOfInterval({
    start: startOfWeek(startOfMonth(pivot.value), { weekStartsOn: weekStartsOn.value }),
    end: endOfWeek(endOfMonth(pivot.value), { weekStartsOn: weekStartsOn.value }),
  })
)

const dowLabels = computed(() => {
  const base = startOfWeek(new Date(), { weekStartsOn: weekStartsOn.value })
  return eachDayOfInterval({ start: base, end: endOfWeek(base, { weekStartsOn: weekStartsOn.value }) })
    .map(d => format(d, 'EEEEE', { locale: fr }).toUpperCase())
})

const monthLabel = computed(() => format(pivot.value, 'MMM yyyy', { locale: fr }))

// Jour sélectionné = query ?date=… quand on est sur le calendrier.
const selectedDate = computed(() => {
  const q = route.query.date
  return typeof q === 'string' ? new Date(`${q}T00:00:00`) : null
})

function openDay(day: Date) {
  router.push(`/calendar?date=${format(day, 'yyyy-MM-dd')}`)
}
</script>

<template>
  <div class="mini-cal">
    <div class="mc-head">
      <span class="mc-label">{{ monthLabel }}</span>
      <span class="mc-nav">
        <button class="mc-btn" @click="pivot = addMonths(pivot, -1)">‹</button>
        <button class="mc-btn" title="Ce mois-ci" @click="pivot = new Date()">•</button>
        <button class="mc-btn" @click="pivot = addMonths(pivot, 1)">›</button>
      </span>
    </div>
    <div class="mc-grid">
      <span v-for="(d, i) in dowLabels" :key="`dow-${i}`" class="mc-dow">{{ d }}</span>
      <button
        v-for="day in days"
        :key="day.toISOString()"
        class="mc-day"
        :class="{
          out: !isSameMonth(day, pivot),
          today: isToday(day),
          selected: selectedDate && isSameDay(day, selectedDate),
        }"
        @click="openDay(day)"
      >{{ format(day, 'd') }}</button>
    </div>
  </div>
</template>

<style scoped>
.mini-cal {
  padding: 8px 12px 10px;
  border-top: 1px solid var(--border);
}
.mc-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}
.mc-label { font-size: 11.5px; font-weight: 600; color: var(--text-secondary); text-transform: capitalize; }
.mc-nav { display: flex; gap: 2px; }
.mc-btn {
  width: 18px; height: 18px;
  display: inline-flex; align-items: center; justify-content: center;
  border: none; background: none; border-radius: 4px;
  color: var(--text-muted); font-size: 12px; cursor: pointer; line-height: 1;
}
.mc-btn:hover { background: var(--bg-hover); color: var(--text); }

.mc-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 1px;
}
.mc-dow {
  font-size: 9px;
  color: var(--text-muted);
  text-align: center;
  padding: 2px 0;
}
.mc-day {
  border: none;
  background: none;
  font-size: 10.5px;
  color: var(--text-secondary);
  padding: 3px 0;
  border-radius: 5px;
  cursor: pointer;
  line-height: 1.2;
}
.mc-day:hover { background: var(--bg-hover); }
.mc-day.out { color: var(--text-muted); opacity: 0.45; }
.mc-day.today { background: var(--primary); color: #fff; font-weight: 600; }
.mc-day.selected:not(.today) { background: var(--primary-soft); color: var(--primary); }
</style>
