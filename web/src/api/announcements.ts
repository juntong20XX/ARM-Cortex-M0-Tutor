/**
 * Announcements API (backend placeholder).
 * Backend should implement GET /api/announcements returning JSON matching AnnouncementsResponse.
 */

export interface Announcement {
  id: string
  title: string
  content: string
  createdAt?: string
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
