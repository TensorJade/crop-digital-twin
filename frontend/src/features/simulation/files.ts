/** Bounded UTF-8 data imports and local downloads, without uploading a filesystem path. */
export const weatherHeader = 'date,tmin_c,tmax_c,rain_mm,radiation_mj_m2,wind_m_s,vapor_kpa'

export async function readInputFile(file: File): Promise<string> {
  if (file.size > 262144) throw new Error('资料文件最多 256 KiB，请缩短范围后重新选择')
  try {
    return new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(
      await file.arrayBuffer(),
    )
  } catch {
    throw new Error('请使用 UTF-8 编码的资料文件')
  }
}

export function parseCropFile(text: string): Record<string, unknown> {
  let data: unknown
  try {
    data = JSON.parse(text.replace(/^\uFEFF/, ''))
  } catch {
    throw new Error('品种参数文件格式不正确，请联系提供文件的农艺人员')
  }
  if (typeof data !== 'object' || data === null || Array.isArray(data))
    throw new Error('品种参数文件应包含品种、适用地区和参数')
  return data as Record<string, unknown>
}

export function downloadData(filename: string, content: string, mime = 'application/json') {
  const url = URL.createObjectURL(new Blob([content], { type: `${mime};charset=utf-8` }))
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.append(anchor)
  anchor.click()
  anchor.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
