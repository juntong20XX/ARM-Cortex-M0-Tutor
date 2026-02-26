<template>
  <div class="project-workspace">
    <div v-if="loading" class="workspace-loading">
      <div class="spinner" />
      <p>Loading project...</p>
    </div>
    <div v-else-if="error" class="workspace-error">
      <p>{{ error }}</p>
      <router-link to="/project/list" class="primary-button">Back to project list</router-link>
    </div>
    <template v-else-if="project">
      <header class="workspace-header">
        <router-link to="/project/list" class="back-link">← Project list</router-link>
        <h1 class="workspace-title">{{ project.name }}</h1>
      </header>
      <DemoWorkspace
        :initial-code="project.content"
        :project-uuid="project.uuid"
        :initial-trace="project.executedTrace"
        :allow-save="false"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import DemoWorkspace from './DemoWorkspace.vue'
import type { TraceResponse } from '@/animation/adl-types'

const route = useRoute()
const router = useRouter()

interface ProjectViewModel {
  uuid: string
  name: string
  content: string
  source: string
  executedTrace: TraceResponse | null
}

const project = ref<ProjectViewModel | null>(null)
const loading = ref(true)
const error = ref('')

async function loadProject(uuid: string) {
  loading.value = true
  error.value = ''
  project.value = null
  try {
    const res = await fetch(`/api/project/info/${uuid}`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      credentials: 'include',
    })
    if (res.status === 401) {
      error.value = 'Please log in to open this project.'
      return
    }
    if (res.status === 403) {
      error.value = 'You do not have permission to open this project.'
      return
    }
    if (res.status === 404) {
      error.value = 'Project not found.'
      return
    }
    if (!res.ok) {
      error.value = `Failed to load project (${res.status}).`
      return
    }
    const data = await res.json()

    const source: string =
      typeof data.source === 'string' ? data.source : ''
    const mergedContent: string =
      source && source.length > 0
        ? source
        : (typeof data.content === 'string' ? data.content : '')

    let executedTrace: TraceResponse | null = null
    if (Array.isArray(data.executed) && data.executed.length > 0) {
      const raw = data.executed[0]
      if (raw && typeof raw === 'object') {
        // 这里假定后端返回的结构已经符合 TraceResponse 规范；若结构不兼容，后续前端会优雅降级。
        executedTrace = raw as TraceResponse
      }
    }

    project.value = {
      uuid: data.uuid,
      name: data.name ?? 'Untitled project',
      content: mergedContent,
      source,
      executedTrace,
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Network error.'
  } finally {
    loading.value = false
  }
}

function ensureUuid() {
  const uuid = route.query.uuid as string | undefined
  if (!uuid || !String(uuid).trim()) {
    router.replace('/project/list')
    return
  }
  loadProject(String(uuid).trim())
}

onMounted(ensureUuid)
watch(() => route.query.uuid, (uuid) => {
  if (uuid && String(uuid).trim()) {
    loadProject(String(uuid).trim())
  } else {
    router.replace('/project/list')
  }
})
</script>

<style scoped>
.project-workspace {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.workspace-loading,
.workspace-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 40vh;
  gap: 1rem;
}

.workspace-error p {
  color: var(--el-color-danger);
  margin: 0;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--el-border-color-lighter);
  border-top-color: var(--el-color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.workspace-header {
  padding: 12px 20px;
  background: var(--el-bg-color-page);
  border-bottom: 1px solid var(--el-border-color-lighter);
  flex-shrink: 0;
}

.back-link {
  font-size: 13px;
  color: var(--el-color-primary);
  text-decoration: none;
  display: inline-block;
  margin-bottom: 6px;
}

.back-link:hover {
  text-decoration: underline;
}

.workspace-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  color: var(--el-text-color-primary);
}
</style>
