/** Identity routes use the same HTTP boundary and in-memory CSRF as farm operations. */
import { jsonPost, requestJson } from '../../api/http'
import type { Page } from '../../api/types'
import type { AuditEvent, Identity, User, UserInput } from './types'

export const getIdentity = () => requestJson<Identity>('/api/v1/auth/me')
export const login = (username: string, password: string) =>
  requestJson<Identity>('/api/v1/auth/login', jsonPost({ username, password }))
export const logout = () => requestJson<{ message: string }>('/api/v1/auth/logout', jsonPost({}))
export const changePassword = (currentPassword: string, newPassword: string) =>
  requestJson<{ message: string }>(
    '/api/v1/auth/password',
    jsonPost({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  )
export const createUser = (data: UserInput) => requestJson<User>('/api/v1/users', jsonPost(data))
export const setUserActive = (id: string, isActive: boolean) =>
  requestJson<User>(
    `/api/v1/users/${encodeURIComponent(id)}/active`,
    jsonPost({ is_active: isActive }),
  )
export const listUsers = (offset = 0) =>
  requestJson<Page<User>>(`/api/v1/users?limit=20&offset=${offset}`)
export const listAudits = (offset = 0) =>
  requestJson<Page<AuditEvent>>(`/api/v1/audit-events?limit=20&offset=${offset}`)
