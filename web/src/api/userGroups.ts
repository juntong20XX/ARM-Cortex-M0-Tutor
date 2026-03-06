/**
 * User groups API for admin: list, create, update, delete.
 */

export interface UserGroup {
  uuid: string
  name: string
  description: string | null
  memberCount: number
}

export interface UserGroupsListResponse {
  items: UserGroup[]
}

export interface CreateUserGroupRequest {
  name: string
  description?: string | null
}

export interface UpdateUserGroupRequest {
  newName?: string | null
  description?: string | null
}

export async function fetchUserGroups(): Promise<UserGroupsListResponse> {
  const res = await fetch('/api/user-groups', {
    method: 'GET',
    credentials: 'include',
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data?.detail || data?.msg || `Failed to fetch user groups: ${res.status}`)
  }
  return res.json()
}

export async function createUserGroup(req: CreateUserGroupRequest): Promise<void> {
  const res = await fetch('/api/user-groups', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: req.name.trim(),
      description: req.description?.trim() || null,
    }),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data?.detail || data?.msg || `Failed to create user group: ${res.status}`)
  }
}

export async function updateUserGroup(
  name: string,
  req: UpdateUserGroupRequest
): Promise<void> {
  const res = await fetch(`/api/user-groups/${encodeURIComponent(name)}`, {
    method: 'PUT',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      newName: req.newName?.trim() || null,
      description: req.description !== undefined ? (req.description?.trim() || null) : undefined,
    }),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data?.detail || data?.msg || `Failed to update user group: ${res.status}`)
  }
}

export async function deleteUserGroup(name: string): Promise<void> {
  const res = await fetch(`/api/user-groups/${encodeURIComponent(name)}`, {
    method: 'DELETE',
    credentials: 'include',
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data?.detail || data?.msg || `Failed to delete user group: ${res.status}`)
  }
}
