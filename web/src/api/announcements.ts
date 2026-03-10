/**
 * Announcements API (backend placeholder).
 * Backend should implement GET /api/announcements returning JSON matching AnnouncementsResponse.
 */

export interface Announcement {
  id: string
  title: string
  content: string
  createdAt?: string
  visibleGroupNames?: string[]
}

export interface AnnouncementsResponse {
  items: Announcement[]
}

export async function fetchAnnouncements(): Promise<AnnouncementsResponse> {
  const res = await fetch('/api/announcements', {
    method: 'GET',
    credentials: 'include',
  })
  if (!res.ok) {
    throw new Error(`Failed to fetch announcements: ${res.status}`)
  }
  const data = await res.json()
  return {
    items: Array.isArray(data?.items) ? data.items : [],
  }
}

export interface CreateAnnouncementRequest {
  title: string
  content: string
  visibleGroupNames?: string[] | null
}

export async function createAnnouncement(req: CreateAnnouncementRequest): Promise<void> {
  const res = await fetch('/api/announcements', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      title: req.title,
      content: req.content,
      visibleGroupNames: req.visibleGroupNames ?? null,
    }),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data?.detail || data?.msg || `Failed to create announcement: ${res.status}`)
  }
}

export async function deleteAnnouncement(announcementUuid: string): Promise<void> {
  const res = await fetch(`/api/announcements/${encodeURIComponent(announcementUuid)}`, {
    method: 'DELETE',
    credentials: 'include',
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data?.detail || data?.msg || `Failed to delete announcement: ${res.status}`)
  }
}
