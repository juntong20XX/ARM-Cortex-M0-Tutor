/**
 * User API for fetching user info, listing users (admin), and deleting users (admin).
 */

export interface UserInfo {
  uuid: string
  display_name: string
  email: string
  groups: string[]
  join_date: string
  last_login: string
  login_source: string
  success?: boolean
  msg?: string
}

export interface UsersListResponse {
  items: UserInfo[]
}

export async function fetchUserInfo(userUuid: string): Promise<UserInfo> {
  const res = await fetch(`/api/user/info/${encodeURIComponent(userUuid)}`, {
    method: 'GET',
    credentials: 'include',
  })
  const data = await res.json()
  if (!res.ok) {
    throw new Error(data?.msg || data?.detail || `HTTP ${res.status}`)
  }
  if (data?.success === false) {
    throw new Error(data?.msg || 'Failed to fetch user info')
  }
  return {
    ...data,
    join_date: data.join_date ? new Date(data.join_date).toLocaleString() : '',
    last_login: data.last_login ? new Date(data.last_login).toLocaleString() : '',
  }
}

export async function fetchAllUsers(): Promise<UsersListResponse> {
  const res = await fetch('/api/users', {
    method: 'GET',
    credentials: 'include',
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data?.detail || data?.msg || `Failed to fetch users: ${res.status}`)
  }
  const data = await res.json()
  const items = Array.isArray(data?.items) ? data.items : []
  return {
    items: items.map((u: Record<string, unknown>) => ({
      ...u,
      join_date: u.join_date ? new Date(u.join_date as string).toLocaleString() : '',
      last_login: u.last_login ? new Date(u.last_login as string).toLocaleString() : '',
    })),
  }
}

export async function deleteUser(userUuid: string): Promise<void> {
  const res = await fetch(`/api/users/${encodeURIComponent(userUuid)}`, {
    method: 'DELETE',
    credentials: 'include',
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data?.detail || data?.msg || `Failed to delete user: ${res.status}`)
  }
}
