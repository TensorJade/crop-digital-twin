/** Actual potential production results, labelled independently of agronomic validation. */
export interface GrowthDay {
  date: string
  dvs: number
  lai: number
  above_ground_kg_ha: number
  storage_organs_kg_ha: number
}
export interface GrowthResult {
  schema_version: string
  model_code: string
  pcse_version: string
  simulation_executed: true
  agronomically_validated: false
  management_effects_applied: false
  assumptions: string[]
  daily: GrowthDay[]
  last_crop_date: string
  input_id: string
  input_hash: string
}
export type RunStatus = 'queued' | 'running' | 'succeeded' | 'failed'
export interface RunSummary {
  id: string
  season_id: string
  input_id: string
  request_key: string
  model_code: string
  engine_version: string
  input_hash: string
  status: RunStatus
  attempts: number
  created_at: string
  finished_at: string | null
  error_code: string | null
  result_hash: string | null
}
export interface RunDetail extends RunSummary {
  result: GrowthResult | null
}
export const runLabels: Record<RunStatus, string> = {
  queued: '等待计算',
  running: '正在计算',
  succeeded: '计算完成',
  failed: '计算失败',
}
export const failureLabels: Record<string, string> = {
  ENGINE_INPUT_REJECTED: '模型拒绝了参数或天气，请联系资料提供者核对后另存输入。',
  ENGINE_TIMEOUT: '计算超过时间限制，请核对输入后重新计算。',
  ENGINE_FAILED: '计算未完成，请联系管理员检查运行环境。',
  ENGINE_UNAVAILABLE: '计算环境不可用，请联系管理员。',
  ENGINE_OUTPUT_INVALID: '计算结果校验未通过，请联系管理员。',
  RESULT_TOO_LARGE: '结果超过保存上限，请缩短资料期间。',
  INPUT_INTEGRITY_FAILED: '输入校验和不一致，请联系管理员核对。',
  ACTOR_UNAVAILABLE: '发起成员已停用或失去写权限，请由管理员重新发起。',
  LEASE_RETRIES_EXHAUSTED: '运行多次中断，请联系管理员检查计算进程后重新发起。',
  ENGINE_VERSION_UNSUPPORTED: '该任务需要不同版本的计算环境，请联系管理员。',
}
