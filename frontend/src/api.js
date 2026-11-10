export async function api(path, options = {}) {
  const response = await fetch(`/api${path}`, {
    ...options,
    headers: options.body instanceof FormData ? options.headers : { 'Content-Type': 'application/json', ...options.headers },
  });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '请求失败，请重试。');
  return data;
}
export const json = (method, value) => ({ method, body: JSON.stringify(value) });
export const activeStates = new Set(['queued', 'running', 'paused', 'needs_login', 'needs_verification']);
export const label = value => value || '未提供';

export function metaText(job) {
  let area = job.area || '';
  if (job.city && area.startsWith(job.city)) area = area.slice(job.city.length).replace(/^[市·\s]+/, '');
  return [job.city, area, job.experience, job.education].filter(Boolean).join(' · ');
}
