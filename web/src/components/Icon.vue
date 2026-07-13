<script setup lang="ts">
/** Icônes filaires monochromes (stroke=currentColor), façon TickTick.
 *  Remplace les emojis pour un rendu natif dans les deux thèmes. */
defineProps<{ name: string; size?: number }>()

const PATHS: Record<string, string> = {
  // Navigation / smart lists
  sun: 'M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10Zm0-15v3m0 14v3M2 12h3m14 0h3M4.9 4.9l2.1 2.1m10 10 2.1 2.1m0-14.2-2.1 2.1m-10 10-2.1 2.1',
  sunrise: 'M12 9a5 5 0 0 1 5 5H7a5 5 0 0 1 5-5Zm0-7v4M4.9 6.9l2.1 2.1m10 0 2.1-2.1M2 18h20M2 14h2m16 0h2',
  'calendar-days': 'M8 2v4m8-4v4M3 9h18M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Zm3 9h.01M12 13h.01M16 13h.01M8 17h.01M12 17h.01M16 17h.01',
  layers: 'M12 2 2 7l10 5 10-5-10-5ZM2 12l10 5 10-5M2 17l10 5 10-5',
  inbox: 'M22 12h-6l-2 3h-4l-2-3H2m3.5-7.6L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.5-7.6A2 2 0 0 0 16.7 3H7.3a2 2 0 0 0-1.8 1.4Z',
  'check-circle': 'M22 11.1V12a10 10 0 1 1-5.9-9.1M22 4 12 14l-3-3',
  calendar: 'M8 2v4m8-4v4M3 10h18M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z',
  timeline: 'M3 5h8M3 12h13M3 19h5m4-14h6m-2 7h6m-11 7h9',
  grid: 'M3 3h8v8H3V3Zm10 0h8v8h-8V3ZM3 13h8v8H3v-8Zm10 0h8v8h-8v-8Z',
  sprout: 'M12 21V9m0 3c0-3.9-3.1-7-7-7H3v1c0 3.9 3.1 7 7 7h2m0-4c0-3.3 2.7-6 6-6h3v1c0 3.3-2.7 6-6 6h-3',
  timer: 'M12 22a8 8 0 1 0 0-16 8 8 0 0 0 0 16Zm0-13v5l3 2M9 2h6',
  'bar-chart': 'M3 21h18M7 21V9m5 12V3m5 18v-7',
  hourglass: 'M6 2h12M6 22h12M8 2v4l4 4 4-4V2M8 22v-4l4-4 4 4v4',
  trash: 'M3 6h18m-2 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m-6 5v6m4-6v6',
  settings: 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm7.4-3a7.4 7.4 0 0 0-.1-1.2l2.1-1.6-2-3.5-2.5 1a7.5 7.5 0 0 0-2-1.2L14.5 3h-5l-.4 2.5a7.5 7.5 0 0 0-2 1.2l-2.5-1-2 3.5L4.7 10.8a7.4 7.4 0 0 0 0 2.4L2.6 14.8l2 3.5 2.5-1a7.5 7.5 0 0 0 2 1.2l.4 2.5h5l.4-2.5a7.5 7.5 0 0 0 2-1.2l2.5 1 2-3.5-2.1-1.6c.1-.4.1-.8.1-1.2Z',
  logout: 'M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4m7 14 5-5-5-5m5 5H9',
  plus: 'M12 5v14M5 12h14',
  folder: 'M4 4h5l2 3h9a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z',
  search: 'M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16Zm10 2-4.3-4.3',
  tag: 'M12 2H2v10l9.3 9.3a2 2 0 0 0 2.8 0l7.2-7.2a2 2 0 0 0 0-2.8L12 2Zm-5 5h.01',
  flag: 'M4 22V4c0-.6.4-1 1-1 3.5 0 5 2 8.5 2 2 0 3.5-.5 5.5-1.5v10c-2 1-3.5 1.5-5.5 1.5-3.5 0-5-2-8.5-2V22',
  pin: 'M12 17v5m-5-9.2V6a2 2 0 0 1 .6-1.4L9 3h6l1.4 1.6A2 2 0 0 1 17 6v6.8l2 2.2H5l2-2.2Z',
  copy: 'M8 8h12v12H8V8Zm-4 8V4h12',
  link: 'M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7',
  'arrow-right': 'M5 12h14m-6-6 6 6-6 6',
  subtask: 'M4 5h16M4 12h4m4 0h8M8 12v5a2 2 0 0 0 2 2h2m0 0h8',
  'link-parent': 'M4 19h16M4 12h16M9 5h11M4 5h.01',
  x: 'M18 6 6 18M6 6l12 12',
  'x-circle': 'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20ZM15 9l-6 6m0-6 6 6',
  dots: 'M5 12h.01M12 12h.01M19 12h.01',
  'chevron-right': 'M9 6l6 6-6 6',
  'chevron-down': 'M6 9l6 6 6-6',
  bell: 'M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9Zm4.3 13a2 2 0 0 0 3.4 0',
  repeat: 'M17 2l4 4-4 4M3 11v-1a4 4 0 0 1 4-4h14M7 22l-4-4 4-4m14-3v1a4 4 0 0 1-4 4H3',
  paperclip: 'm21.4 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48',
  comment: 'M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10Z',
  sort: 'M8 3v18m0 0-4-4m4 4 4-4m4-14v10m0-10 4 4m-4-4-4 4',
  moon: 'M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8Z',
  monitor: 'M3 4h18v12H3V4Zm5 16h8m-4-4v4',
  filter: 'M22 3H2l8 9.5V19l4 2v-8.5L22 3Z',
  archive: 'M3 3h18v5H3V3Zm1 5v12a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1V8M10 12h4',
  play: 'M6 4l14 8-14 8V4Z',
  import: 'M12 3v12m0 0-4-4m4 4 4-4M4 21h16',
  export: 'M12 15V3m0 0L8 7m4-4 4 4M4 21h16',
  printer: 'M6 9V2h12v7M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2m-12-4h12v8H6v-8Z',
}
</script>

<template>
  <svg
    :width="size ?? 16"
    :height="size ?? 16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.7"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path :d="PATHS[name] ?? PATHS.dots" />
  </svg>
</template>
