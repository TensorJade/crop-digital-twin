/** Public account facts only; session authentication tokens are never available to JavaScript. */
export type Role = 'owner' | 'operator' | 'viewer'
export interface User {
  id: string
  organization_id: string
  username: string
  display_name: string
  role: Role
  is_active: boolean
  created_at: string
}
export interface Organization {
  id: string
  name: string
  created_at: string
}
export interface Identity {
  user: User
  organization: Organization
  csrf_token: string
  expires_at: string
}
export interface UserInput {
  username: string
  display_name: string
  role: 'operator' | 'viewer'
  password: string
}
export interface AuditEvent {
  id: string
  actor_user_id: string
  actor_display_name: string | null
  action: string
  entity_type: string
  entity_id: string
  created_at: string
}
export const roleLabels: Record<Role, string> = {
  owner: '管理员',
  operator: '农田管理',
  viewer: '仅查看',
}
export const actionLabels: Record<string, string> = {
  'identity.bootstrap': '建立组织与管理员',
  'identity.legacy_adopted': '接收旧地块',
  'identity.user_created': '建立成员账号',
  'identity.user_activated': '启用成员',
  'identity.user_deactivated': '停用成员',
  'auth.login': '登录',
  'auth.logout': '退出登录',
  'auth.password_changed': '修改密码',
  'farm.plot_created': '登记地块',
  'farm.season_created': '建立种植季',
  'farm.season_closed': '结束种植季',
  'farm.event_created': '登记农事',
  'farm.event_corrected': '修正农事',
}
