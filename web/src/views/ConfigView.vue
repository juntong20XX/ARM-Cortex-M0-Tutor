<template>
  <section class="panel">
    <p class="eyebrow">ARM Cortex-M0 Tutorial</p>
    <h1 class="title">Config</h1>
    <p class="lead">
      User information and configuration. Administrators can manage users and announcements.
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

const { userUuid } = useSession()
const loading = ref(true)
const error = ref<string | null>(null)
const userList = ref<UserInfo[]>([])
const isAdmin = ref(false)
const announcementsList = ref<Announcement[]>([])
const announcementsLoading = ref(false)
const publishLoading = ref(false)
const announceForm = ref({ title: '', content: '' })

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

async function load() {
  await loadUserData()
  await loadAnnouncements()
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
