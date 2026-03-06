<template>
  <section class="panel">
    <p class="eyebrow">Home</p>
    <h1 class="title">Announcements</h1>

    <div v-if="loading" class="state state-loading">Loading…</div>
    <div v-else-if="error" class="state state-error">
      <p>{{ error }}</p>
      <button type="button" class="retry-btn" @click="load">Retry</button>
    </div>
    <div v-else-if="!list.length" class="state state-empty">No announcements</div>
    <ul v-else class="announcement-list">
      <li v-for="item in list" :key="item.id" class="announcement-item">
        <h2 class="announcement-title">{{ item.title }}</h2>
        <p v-if="item.createdAt" class="announcement-date">{{ item.createdAt }}</p>
        <p class="announcement-content">{{ item.content }}</p>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { fetchAnnouncements } from '../api/announcements'
import type { Announcement } from '../api/announcements'

const list = ref<Announcement[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    const res = await fetchAnnouncements()
    list.value = res.items
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Load failed'
    list.value = []
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.panel {
  width: 100%;
  max-width: 1280px;
  margin: 0 auto;
  padding: 2.5vh 2vw 3vh;
  border-radius: 18px;
  border: 1px solid #e5e7eb;
  background: #ffffff;
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
}

.state {
  padding: 24px 0;
  text-align: center;
  color: #6b7280;
}

.state-loading {
  font-size: 14px;
}

.state-error p {
  margin: 0 0 12px;
  font-size: 14px;
  color: #b91c1c;
}

.retry-btn {
  padding: 6px 14px;
  font-size: 14px;
  font-weight: 600;
  color: #2563eb;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  cursor: pointer;
}

.retry-btn:hover {
  background: #dbeafe;
}

.announcement-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.announcement-item {
  padding: 16px 0;
  border-bottom: 1px solid #e5e7eb;
}

.announcement-item:last-child {
  border-bottom: none;
}

.announcement-title {
  margin: 0 0 6px;
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

.announcement-date {
  margin: 0 0 8px;
  font-size: 12px;
  color: #6b7280;
}

.announcement-content {
  margin: 0;
  font-size: 14px;
  line-height: 1.6;
  color: #374151;
}
</style>
