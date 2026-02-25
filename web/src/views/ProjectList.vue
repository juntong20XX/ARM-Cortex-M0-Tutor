<script setup>
import { onMounted, computed, ref } from 'vue'
import { RouterLink } from 'vue-router'

const projects = ref([])
const loading = ref(true)
const loadError = ref(false)

const showCreateForm = ref(false)
const creating = ref(false)
const createError = ref('')
const createSuccess = ref(false)
const createForm = ref({
  name: '',
  content: '',
  description: '',
  source: '',
})

const showEditForm = ref(false)
const editing = ref(false)
const editError = ref('')
const editTargetUuid = ref('')
const editForm = ref({ name: '', description: '', content: '', source: '' })

const deletingUuid = ref('')
const deleteError = ref('')

const demoProjects = [
  {
    id: 'demo-blinky',
    name: 'Blinky LED',
    description: 'Classic ARM Cortex-M0 getting-started example demonstrating GPIO configuration and delay loops.',
    level: 'Beginner',
    tags: ['GPIO', 'basic'],
  },
  {
    id: 'demo-systick',
    name: 'SysTick Timer',
    description: 'Use the SysTick timer to generate periodic interrupts and observe register changes.',
    level: 'Intermediate',
    tags: ['timer', 'interrupt'],
  },
  {
    id: 'demo-uart',
    name: 'UART Echo',
    description: 'Echo data over UART to practice peripheral initialization and simple protocols.',
    level: 'Intermediate',
    tags: ['UART', 'peripheral'],
  },
]

/** 当前用于展示的列表：接口成功用 projects，失败用 demoProjects */
const displayProjects = computed(() => {
  if (projects.value && projects.value.length > 0) {
    return projects.value
  }
  return demoProjects
})

function getProjectListFromResponse(payload) {
  if (!payload) return null
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload.data)) return payload.data
  return null
}

function getProjectTitle(project) {
  return project.name || project.title || project.id || 'Untitled project'
}

function getProjectDescription(project) {
  return (
    project.description ||
    project.summary ||
    'This project comes from the backend response and does not provide a detailed description yet.'
  )
}

function getProjectLevel(project) {
  return project.level || project.difficulty || ''
}

function getProjectTags(project) {
  if (Array.isArray(project.tags)) return project.tags
  return []
}

function getProjectLink(project) {
  const uuid = project.uuid
  if (uuid) {
    return { path: '/project/workspace', query: { uuid } }
  }
  const name = project.name || project.title || project.id
  if (name) {
    return { path: '/demo', query: { project: name } }
  }
  return { path: '/demo' }
}

async function loadProjects() {
  loading.value = true
  loadError.value = false

  try {
    const res = await fetch('/api/project/list', {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
    })

    if (!res.ok) {
      throw new Error(`Request failed with status ${res.status}`)
    }

    const json = await res.json()
    const list = getProjectListFromResponse(json)

    if (!list || !Array.isArray(list) || list.length === 0) {
      throw new Error('Invalid or empty project list')
    }

    projects.value = list
  } catch (err) {
    console.error('[ProjectList] Failed to load project list:', err)
    loadError.value = true
    projects.value = demoProjects
  } finally {
    loading.value = false
  }
}

function openCreateForm() {
  showCreateForm.value = true
  createError.value = ''
  createSuccess.value = false
  createForm.value = { name: '', content: '', description: '', source: '' }
}

function closeCreateForm() {
  showCreateForm.value = false
  createError.value = ''
  createSuccess.value = false
}

async function openEditForm(project) {
  if (!project || !project.uuid) return
  closeCreateForm()
  showEditForm.value = true
  editError.value = ''
  editTargetUuid.value = project.uuid
  editForm.value = {
    name: project.name ?? '',
    description: project.description ?? '',
    content: project.content ?? '',
    source: '',
  }
  try {
    const res = await fetch('/api/project/info/' + encodeURIComponent(project.uuid), {
      method: 'GET',
      headers: { Accept: 'application/json' },
      credentials: 'include',
    })
    if (res.ok) {
      const data = await res.json()
      editForm.value.source = (data.source || '').toString()
    }
  } catch (err) {
    console.error('[ProjectList] Failed to load project source for edit:', err)
  }
}

function closeEditForm() {
  showEditForm.value = false
  editError.value = ''
  editForm.value = { name: '', description: '', content: '', source: '' }
}

async function submitEditProject() {
  const { name, description, content, source } = editForm.value
  if (!name || !name.trim()) {
    editError.value = 'Please enter a project name'
    return
  }
  editing.value = true
  editError.value = ''
  try {
    const uuid = editTargetUuid.value
    const metaRes = await fetch('/api/project/update/' + encodeURIComponent(uuid), {
      method: 'PUT',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({
        name: name.trim(),
        description: (description || '').trim() || null,
        content: (content || '').trim() || null,
      }),
    })
    if (!metaRes.ok) {
      const data = await metaRes.json().catch(() => ({}))
      editError.value = data.detail || data.msg || `Update failed (${metaRes.status})`
      return
    }

    const sourceRes = await fetch('/api/project/source/' + encodeURIComponent(uuid), {
      method: 'PUT',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ source: (source || '').toString() }),
    })
    if (!sourceRes.ok) {
      const data = await sourceRes.json().catch(() => ({}))
      editError.value = data.detail || data.msg || `Update source failed (${sourceRes.status})`
      return
    }

    closeEditForm()
    await loadProjects()
  } catch (err) {
    console.error('[ProjectList] Edit project failed:', err)
    editError.value = err.message || 'Network error'
  } finally {
    editing.value = false
  }
}

async function deleteProject(project) {
  if (!project || !project.uuid) return
  const title = getProjectTitle(project)
  if (!window.confirm(`Delete project "${title}"? This cannot be undone.`)) return
  deletingUuid.value = project.uuid
  deleteError.value = ''
  try {
    const res = await fetch('/api/project/delete/' + encodeURIComponent(project.uuid), {
      method: 'DELETE',
      credentials: 'include',
      headers: { Accept: 'application/json' },
    })
    if (res.ok) {
      await loadProjects()
    } else {
      const data = await res.json().catch(() => ({}))
      deleteError.value = data.detail || data.msg || `Delete failed (${res.status})`
    }
  } catch (err) {
    console.error('[ProjectList] Delete project failed:', err)
    deleteError.value = err.message || 'Network error'
  } finally {
    deletingUuid.value = ''
  }
}

async function submitCreateProject() {
  const { name, content, description, source } = createForm.value
  if (!name || !name.trim()) {
    createError.value = 'Please enter a project name'
    return
  }
  creating.value = true
  createError.value = ''
  createSuccess.value = false
  const now = new Date().toISOString()
  const body = {
    success: true,
    msg: '',
    uuid: '',
    name: name.trim(),
    content: (content || '').trim(),
    description: (description || '').trim() || null,
    source: (source || '').trim(),
    code: [],
    executed: [],
    owner_id: '',
    owner_name: '',
    created_at: now,
    updated_at: now,
  }
  try {
    const res = await fetch('/api/project/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      credentials: 'include',
      body: JSON.stringify(body),
    })
    if (res.status === 201) {
      createSuccess.value = true
      closeCreateForm()
      await loadProjects()
    } else {
      const data = await res.json().catch(() => ({}))
      createError.value = data.detail || data.msg || `Create failed (${res.status})`
    }
  } catch (err) {
    console.error('[ProjectList] Create project failed:', err)
    createError.value = err.message || 'Network error'
  } finally {
    creating.value = false
  }
}

onMounted(() => {
  loadProjects()
})
</script>

<template>
  <section class="panel">
    <p class="eyebrow">ARM Cortex-M0 Tutorial</p>
    <h1 class="title">Project</h1>
    <p class="lead">
      Manage and explore ARM Cortex-M0 tutorial projects. Pick a project to read the guide, inspect assembly source code, and run simulations.
    </p>

    <div class="toolbar">
      <button type="button" class="primary-button" @click="openCreateForm">
        New Project
      </button>
    </div>

    <div v-if="showCreateForm" class="create-form-wrap">
      <h3 class="create-form-title">New Project</h3>
      <form class="create-form" @submit.prevent="submitCreateProject">
        <div class="form-row">
          <label for="create-name">Project Name <span class="required">*</span></label>
          <input
            id="create-name"
            v-model="createForm.name"
            type="text"
            placeholder="e.g. Blinky LED"
            class="form-input"
            required
          />
        </div>
        <div class="form-row">
          <label for="create-description">Description</label>
          <input
            id="create-description"
            v-model="createForm.description"
            type="text"
            placeholder="Brief description of the project"
            class="form-input"
          />
        </div>
        <div class="form-row">
          <label for="create-content">Content Description</label>
          <textarea
            id="create-content"
            v-model="createForm.content"
            placeholder="Project description or tutorial content (optional)"
            class="form-input form-textarea"
            rows="2"
          />
        </div>
        <div class="form-row">
          <label for="create-source">Initial Assembly Source</label>
          <textarea
            id="create-source"
            v-model="createForm.source"
            placeholder="Optional, leave blank to start from an empty project"
            class="form-input form-textarea form-source"
            rows="6"
          />
        </div>
        <p v-if="createError" class="state state-error">{{ createError }}</p>
        <div class="form-actions">
          <button type="button" class="secondary-button" @click="closeCreateForm">
            Cancel
          </button>
          <button type="submit" class="primary-button" :disabled="creating">
            {{ creating ? 'Creating...' : 'Create' }}
          </button>
        </div>
      </form>
    </div>

    <div v-if="showEditForm" class="create-form-wrap">
      <h3 class="create-form-title">Edit Project</h3>
      <form class="create-form" @submit.prevent="submitEditProject">
        <div class="form-row">
          <label for="edit-name">Project Name <span class="required">*</span></label>
          <input
            id="edit-name"
            v-model="editForm.name"
            type="text"
            placeholder="e.g. Blinky LED"
            class="form-input"
            required
          />
        </div>
        <div class="form-row">
          <label for="edit-description">Description</label>
          <input
            id="edit-description"
            v-model="editForm.description"
            type="text"
            placeholder="Brief description of the project"
            class="form-input"
          />
        </div>
        <div class="form-row">
          <label for="edit-content">Content Description</label>
          <textarea
            id="edit-content"
            v-model="editForm.content"
            placeholder="Project description or tutorial content (optional)"
            class="form-input form-textarea"
            rows="2"
          />
        </div>
        <div class="form-row">
          <label for="edit-source">Assembly Source</label>
          <textarea
            id="edit-source"
            v-model="editForm.source"
            placeholder="Edit project assembly source code (optional)"
            class="form-input form-textarea form-source"
            rows="6"
          />
        </div>
        <p v-if="editError" class="state state-error">{{ editError }}</p>
        <div class="form-actions">
          <button type="button" class="secondary-button" @click="closeEditForm">
            Cancel
          </button>
          <button type="submit" class="primary-button" :disabled="editing">
            {{ editing ? 'Saving...' : 'Save changes' }}
          </button>
        </div>
      </form>
    </div>

    <p v-if="deleteError" class="state state-error">{{ deleteError }}</p>

    <div v-if="loading" class="state state-loading">
      <div class="spinner" />
      <p>Loading project list...</p>
    </div>

    <div v-else class="content">
      <p v-if="loadError" class="state state-error">
        Failed to load the project list from the server. Showing a local demo project instead.
      </p>

      <div class="project-grid">
        <article
          v-for="project in displayProjects"
          :key="project.uuid || project.id || project.name || project.title"
          class="project-card"
        >
          <header class="project-card-header">
            <h2 class="project-title">
              {{ getProjectTitle(project) }}
            </h2>
            <span v-if="getProjectLevel(project)" class="badge badge-level">
              {{ getProjectLevel(project) }}
            </span>
          </header>

          <p class="project-description">
            {{ getProjectDescription(project) }}
          </p>

          <ul v-if="getProjectTags(project).length" class="tag-list">
            <li v-for="tag in getProjectTags(project)" :key="tag" class="tag">
              {{ tag }}
            </li>
          </ul>

          <footer class="project-footer">
            <RouterLink
              :to="getProjectLink(project)"
              class="primary-button"
            >
              Open project
            </RouterLink>
            <template v-if="project.uuid">
              <button
                type="button"
                class="secondary-button"
                @click="openEditForm(project)"
              >
                Edit
              </button>
              <button
                type="button"
                class="danger-button"
                :disabled="deletingUuid === project.uuid"
                @click="deleteProject(project)"
              >
                {{ deletingUuid === project.uuid ? 'Deleting...' : 'Delete' }}
              </button>
            </template>
          </footer>
        </article>
      </div>
    </div>
  </section>
</template>

<style scoped>
.panel {
  max-width: 1280px;
  margin: 0 auto;
  padding: 24px 20px 28px;
  border-radius: 18px;
  border: 1px solid #e5e7eb;
  background: #ffffff;
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.eyebrow {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #6b7280;
}

.title {
  font-size: 26px;
  font-weight: 700;
  color: #111827;
  letter-spacing: -0.03em;
}

.lead {
  font-size: 14px;
  line-height: 1.6;
  color: #4b5563;
  max-width: 720px;
}

.toolbar {
  display: flex;
  gap: 10px;
}

.create-form-wrap {
  padding: 18px;
  border-radius: 14px;
  border: 1px solid #e5e7eb;
  background: #f9fafb;
}

.create-form-title {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 14px;
}

.create-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-row label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 4px;
}

.form-row .required {
  color: #dc2626;
}

.form-input {
  width: 100%;
  padding: 8px 10px;
  font-size: 14px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #fff;
  box-sizing: border-box;
}

.form-input:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2);
}

.form-textarea {
  resize: vertical;
  min-height: 60px;
}

.form-source {
  font-family: ui-monospace, monospace;
  font-size: 13px;
}

.form-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 6px;
}

.secondary-button {
  padding: 6px 12px;
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  background: #fff;
  border: 1px solid #d1d5db;
  border-radius: 999px;
  cursor: pointer;
}

.secondary-button:hover {
  background: #f3f4f6;
}

.content {
  margin-top: 4px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.state {
  font-size: 13px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 999px;
}

.state-loading {
  background: #eff6ff;
  color: #1d4ed8;
}

.state-error {
  background: #fef2f2;
  color: #b91c1c;
}

.spinner {
  width: 14px;
  height: 14px;
  border-radius: 999px;
  border: 2px solid rgba(59, 130, 246, 0.25);
  border-top-color: #2563eb;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 14px;
}

.project-card {
  border-radius: 14px;
  border: 1px solid #e5e7eb;
  padding: 14px 14px 12px;
  background: radial-gradient(circle at top left, #eff6ff 0, #ffffff 45%);
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}

.project-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.12);
  border-color: #bfdbfe;
}

.project-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.project-title {
  font-size: 15px;
  font-weight: 700;
  color: #111827;
}

.badge {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 999px;
  border: 1px solid transparent;
  white-space: nowrap;
}

.badge-level {
  background: #ecfeff;
  border-color: #a5f3fc;
  color: #0f766e;
}

.project-description {
  font-size: 13px;
  line-height: 1.5;
  color: #4b5563;
}

.tag-list {
  display: flex;

  flex-wrap: wrap;
  gap: 6px;
}

.tag {
  font-size: 11px;
  padding: 3px 7px;
  border-radius: 999px;
  background: #f3f4f6;
  color: #4b5563;
}

.project-footer {
  margin-top: 4px;
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.danger-button {
  padding: 6px 12px;
  font-size: 13px;
  font-weight: 600;
  color: #fff;
  background: #dc2626;
  border: 1px solid #b91c1c;
  border-radius: 999px;
  cursor: pointer;
}

.danger-button:hover:not(:disabled) {
  background: #b91c1c;
}

.danger-button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.primary-button {
  border: none;
  outline: none;
  cursor: pointer;
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  color: #ffffff;
  background: linear-gradient(135deg, #2563eb, #4f46e5);
  box-shadow: 0 6px 18px rgba(37, 99, 235, 0.35);
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.primary-button:hover {
  filter: brightness(1.05);
}

.primary-button:active {
  transform: translateY(1px);
  box-shadow: 0 3px 10px rgba(37, 99, 235, 0.4);
}

@media (max-width: 768px) {
  .panel {
    padding: 18px 14px 22px;
  }

  .title {
    font-size: 22px;
  }
}
</style>
