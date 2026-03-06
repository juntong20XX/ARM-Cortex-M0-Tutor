<template>
  <section class="panel">
    <p class="eyebrow">ARM Cortex-M0 Tutorial</p>
    <h1 class="title">Config</h1>
    <p class="lead">
      User information and configuration. Administrators can manage users, announcements, and user groups.
    </p>

    <!-- Loading / Error -->
    <div v-if="loading" class="state state-loading">Loading…</div>
    <div v-else-if="error" class="state state-error">
      <p>{{ error }}</p>
      <button type="button" class="retry-btn" @click="load">Retry</button>
    </div>

    <!-- User Table -->
    <template v-else>
      <h2 class="section-title">User Information</h2>
      <el-table :data="userList" stripe border class="user-table">
        <el-table-column prop="display_name" label="Display Name" min-width="120">
          <template #default="{ row }">
            <el-text type="success" tag="b">{{ row.display_name }}</el-text>
          </template>
        </el-table-column>
        <el-table-column prop="email" label="Email" min-width="180">
          <template #default="{ row }">
            <el-link type="primary" :underline="false">{{ row.email }}</el-link>
          </template>
        </el-table-column>
        <el-table-column prop="join_date" label="Joined At" width="160" />
        <el-table-column prop="last_login" label="Last Login" width="160" />
        <el-table-column prop="login_source" label="Login Source" width="120">
          <template #default="{ row }">
            <el-tag type="warning" effect="plain" size="small">{{ row.login_source }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="groups" label="Groups" min-width="140">
          <template #default="{ row }">
            <el-space wrap>
              <el-tag
                v-for="g in (row.groups || [])"
                :key="g"
                type="success"
                effect="light"
                size="small"
              >
                {{ g }}
              </el-tag>
              <el-text v-if="!row.groups?.length" type="info" size="small">None</el-text>
            </el-space>
          </template>
        </el-table-column>
        <el-table-column v-if="isAdmin" label="Actions" width="100" fixed="right">
          <template #default="{ row }">
            <el-button
              type="danger"
              size="small"
              :disabled="row.uuid === userUuid"
              @click="handleDeleteUser(row.uuid)"
            >
              Delete
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- Admin: Publish Announcement -->
      <template v-if="isAdmin">
        <h2 class="section-title">Publish Announcement</h2>
        <el-form :model="announceForm" class="announce-form" label-position="top">
          <el-form-item label="Title">
            <el-input v-model="announceForm.title" placeholder="Announcement title" />
          </el-form-item>
          <el-form-item label="Content">
            <el-input
              v-model="announceForm.content"
              type="textarea"
              :rows="4"
              placeholder="Announcement content"
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="publishLoading" @click="handlePublishAnnouncement">
              Publish
            </el-button>
          </el-form-item>
        </el-form>

        <!-- Admin: User Groups -->
        <h2 class="section-title">Manage User Groups</h2>
        <el-form :model="groupForm" class="group-form" label-position="top">
          <el-form-item v-if="!editingGroupName" label="Create group">
            <div class="group-form-row">
              <el-input
                v-model="groupForm.name"
                placeholder="Group name"
                style="max-width: 200px"
              />
              <el-input
                v-model="groupForm.description"
                placeholder="Description (optional)"
                style="max-width: 280px"
              />
              <el-button type="primary" :loading="groupLoading" @click="handleCreateGroup">
                Create
              </el-button>
            </div>
          </el-form-item>
          <el-form-item v-else label="Edit group">
            <div class="group-form-row">
              <el-input
                v-model="groupForm.name"
                placeholder="New name"
                style="max-width: 200px"
              />
              <el-input
                v-model="groupForm.description"
                placeholder="Description (optional)"
                style="max-width: 280px"
              />
              <el-button type="primary" :loading="groupLoading" @click="handleUpdateGroup">
                Save
              </el-button>
              <el-button @click="cancelEditGroup">Cancel</el-button>
            </div>
          </el-form-item>
        </el-form>
        <div v-if="groupsLoading" class="state state-loading">Loading user groups…</div>
        <el-table v-else :data="groupsList" stripe border class="group-table">
          <el-table-column prop="name" label="Name" min-width="140" />
          <el-table-column prop="description" label="Description" min-width="200">
            <template #default="{ row }">
              {{ row.description || '—' }}
            </template>
          </el-table-column>
          <el-table-column prop="memberCount" label="Members" width="100" />
          <el-table-column label="Actions" width="140">
            <template #default="{ row }">
              <el-button
                type="primary"
                size="small"
                link
                :disabled="isSystemGroup(row.name)"
                @click="openEditGroup(row)"
              >
                Edit
              </el-button>
              <el-button
                type="danger"
                size="small"
                link
                :disabled="isSystemGroup(row.name)"
                @click="handleDeleteGroup(row.name)"
              >
                Delete
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- Admin: Announcements List -->
        <h2 class="section-title">Manage Announcements</h2>
        <div v-if="announcementsLoading" class="state state-loading">Loading announcements…</div>
        <ul v-else-if="!announcementsList.length" class="announcement-list state-empty">
          No announcements
        </ul>
        <ul v-else class="announcement-list">
          <li v-for="item in announcementsList" :key="item.id" class="announcement-item">
            <div class="announcement-header">
              <h3 class="announcement-title">{{ item.title }}</h3>
              <el-button type="danger" size="small" @click="handleDeleteAnnouncement(item.id)">
                Delete
              </el-button>
            </div>
            <p v-if="item.createdAt" class="announcement-date">{{ item.createdAt }}</p>
            <p class="announcement-content">{{ item.content }}</p>
          </li>
        </ul>
      </template>
    </template>
  </section>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useSession } from '../composables/useSession'
import { fetchUserInfo, fetchAllUsers, deleteUser, type UserInfo } from '../api/user'
import {
  fetchAnnouncements,
  createAnnouncement,
  deleteAnnouncement,
  type Announcement,
} from '../api/announcements'
import {
  fetchUserGroups,
  createUserGroup,
  updateUserGroup,
  deleteUserGroup,
  type UserGroup,
} from '../api/userGroups'

const { userUuid } = useSession()
const loading = ref(true)
const error = ref<string | null>(null)
const userList = ref<UserInfo[]>([])
const isAdmin = ref(false)
const announcementsList = ref<Announcement[]>([])
const announcementsLoading = ref(false)
const publishLoading = ref(false)
const announceForm = ref({ title: '', content: '' })
const groupsList = ref<UserGroup[]>([])
const groupsLoading = ref(false)
const groupLoading = ref(false)
const editingGroupName = ref<string | null>(null)
const groupForm = ref({ name: '', description: '' })

async function loadUserData() {
  if (!userUuid.value) {
    error.value = 'Not logged in'
    return
  }
  loading.value = true
  error.value = null
  try {
    const info = await fetchUserInfo(userUuid.value)
    userList.value = [info]
    isAdmin.value = (info.groups || []).includes('administrator')
    if (isAdmin.value) {
      const usersRes = await fetchAllUsers()
      userList.value = usersRes.items
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Load failed'
    userList.value = []
  } finally {
    loading.value = false
  }
}

async function loadAnnouncements() {
  if (!isAdmin.value) return
  announcementsLoading.value = true
  try {
    const res = await fetchAnnouncements()
    announcementsList.value = res.items
  } catch {
    announcementsList.value = []
  } finally {
    announcementsLoading.value = false
  }
}

async function loadUserGroups() {
  if (!isAdmin.value) return
  groupsLoading.value = true
  try {
    const res = await fetchUserGroups()
    groupsList.value = res.items
  } catch {
    groupsList.value = []
  } finally {
    groupsLoading.value = false
  }
}

async function load() {
  await loadUserData()
  await loadAnnouncements()
  await loadUserGroups()
}

const SYSTEM_GROUPS = ['everyone', 'administrator']
function isSystemGroup(name: string) {
  return SYSTEM_GROUPS.includes(name)
}

function openEditGroup(group: UserGroup) {
  editingGroupName.value = group.name
  groupForm.value = { name: group.name, description: group.description || '' }
}

function cancelEditGroup() {
  editingGroupName.value = null
  groupForm.value = { name: '', description: '' }
}

async function handleCreateGroup() {
  const { name, description } = groupForm.value
  if (!name.trim()) {
    ElMessage.warning('Please enter a group name')
    return
  }
  groupLoading.value = true
  try {
    await createUserGroup({ name: name.trim(), description: description.trim() || null })
    ElMessage.success({ message: 'Group created successfully', showClose: true })
    groupForm.value = { name: '', description: '' }
    await loadUserGroups()
  } catch (e) {
    const msg = e instanceof Error ? e.message : 'Group creation failed'
    ElMessage.error({ message: msg, showClose: true })
  } finally {
    groupLoading.value = false
  }
}

async function handleUpdateGroup() {
  const orig = editingGroupName.value
  if (!orig) return
  const { name, description } = groupForm.value
  groupLoading.value = true
  try {
    await updateUserGroup(orig, {
      newName: name.trim() || orig,
      description: description.trim() || null,
    })
    ElMessage.success('User group updated')
    cancelEditGroup()
    await loadUserGroups()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : 'Update failed')
  } finally {
    groupLoading.value = false
  }
}

async function handleDeleteGroup(name: string) {
  if (isSystemGroup(name)) return
  try {
    await ElMessageBox.confirm(
      `Delete user group "${name}"? Users in this group will be removed from it.`,
      'Confirm Delete',
      { type: 'warning' }
    )
    await deleteUserGroup(name)
    ElMessage.success('User group deleted')
    if (editingGroupName.value === name) cancelEditGroup()
    await loadUserGroups()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e instanceof Error ? e.message : 'Delete failed')
    }
  }
}

async function handleDeleteUser(uuid: string) {
  try {
    await ElMessageBox.confirm(
      'Are you sure you want to delete this user? This action cannot be undone.',
      'Confirm Delete',
      { type: 'warning' }
    )
    await deleteUser(uuid)
    ElMessage.success('User deleted successfully')
    await loadUserData()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e instanceof Error ? e.message : 'Delete failed')
    }
  }
}

async function handlePublishAnnouncement() {
  const { title, content } = announceForm.value
  if (!title.trim() || !content.trim()) {
    ElMessage.warning('Please fill in title and content')
    return
  }
  publishLoading.value = true
  try {
    await createAnnouncement({ title: title.trim(), content: content.trim() })
    ElMessage.success('Announcement published')
    announceForm.value = { title: '', content: '' }
    await loadAnnouncements()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : 'Publish failed')
  } finally {
    publishLoading.value = false
  }
}

async function handleDeleteAnnouncement(id: string) {
  try {
    await ElMessageBox.confirm(
      'Are you sure you want to delete this announcement?',
      'Confirm Delete',
      { type: 'warning' }
    )
    await deleteAnnouncement(id)
    ElMessage.success('Announcement deleted')
    await loadAnnouncements()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e instanceof Error ? e.message : 'Delete failed')
    }
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

.eyebrow {
  margin: 0 0 4px;
  font-size: 12px;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.title {
  margin: 0 0 8px;
  font-size: 24px;
  font-weight: 600;
  color: #111827;
}

.lead {
  margin: 0 0 24px;
  font-size: 14px;
  line-height: 1.6;
  color: #6b7280;
}

.section-title {
  margin: 28px 0 12px;
  font-size: 16px;
  font-weight: 600;
  color: #374151;
}

.section-title:first-of-type {
  margin-top: 0;
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

.user-table {
  margin-top: 8px;
}

.announce-form {
  max-width: 560px;
}

.group-form {
  max-width: 640px;
}

.group-form-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.group-table {
  margin-top: 8px;
  max-width: 640px;
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

.announcement-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.announcement-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

.announcement-date {
  margin: 6px 0 8px;
  font-size: 12px;
  color: #6b7280;
}

.announcement-content {
  margin: 0;
  font-size: 14px;
  line-height: 1.6;
  color: #374151;
}

.state-empty {
  padding: 16px 0;
  color: #9ca3af;
  font-size: 14px;
}
</style>
