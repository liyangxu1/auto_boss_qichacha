import { useEffect, useRef, useState } from 'react';
import Icon from './Icon';
const experiences = ['经验不限', '在校/应届', '1年以内', '1-3年', '3-5年', '5-10年', '10年以上'];
export default function SearchPanel({ data, busy, browser, onUpload, onResume, onRetry, onGenerate, onSave, onCollect, onConnect }) {
  const [form, setForm] = useState({ cities: '', target_directions: '', experience_filter: '1-3年', experience_note: '', primary_search_keywords: [] });
  const [keyword, setKeyword] = useState('');
  const [dirty, setDirty] = useState(false);
  const [limits, setLimits] = useState({ max_jobs_per_search: 6, max_jobs_total: 36, collect_company_details: false });
  const [dragging, setDragging] = useState(false);
  const file = useRef(null);
  const version = JSON.stringify([data?.project.id, data?.search, data?.project.preferences]);
  useEffect(() => {
    const search = data?.search;
    const prefs = data?.project.preferences || {};
    setForm({ cities: (search?.cities || prefs.cities || []).join('、'), target_directions: prefs.target_directions || '',
      employment_type: prefs.employment_type || '全职', experience_filter: search?.experience_filter || '1-3年', experience_note: prefs.experience_note || search?.experience_note || '',
      primary_search_keywords: search?.primary_search_keywords || [] });
    setDirty(false);
  }, [version]);
  function edit(key, value) { setForm(old => ({ ...old, [key]: value })); setDirty(true); }
  const cities = () => form.cities.split(/[、，,;；\n]/).map(s => s.trim()).filter(Boolean);
  function addKeyword(event) {
    event.preventDefault();
    const value = keyword.trim();
    if (value && value.length <= 30 && !form.primary_search_keywords.includes(value) && form.primary_search_keywords.length < 6) {
      edit('primary_search_keywords', [...form.primary_search_keywords, value]); setKeyword('');
    }
  }
  const preferences = () => ({ cities: cities(), target_directions: form.target_directions, employment_type: form.employment_type, experience_note: form.experience_note });
  async function save() { return onSave({ ...form, cities: cities() }); }
  async function collect() { if (await save()) onCollect(limits); }
  const canSearch = data?.resume && data?.search && form.primary_search_keywords.length && cities().length;
  return <aside className="panel search-panel">
    <div className="panel-heading"><h2>简历与搜索</h2><Icon name="settings" size={17}/></div>
    <button className={`upload-zone ${dragging ? 'dragging' : ''}`} onClick={() => file.current.click()} disabled={busy}
      onDragOver={e => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)}
      onDrop={e => { e.preventDefault(); setDragging(false); if (!busy && e.dataTransfer.files[0]) onUpload(e.dataTransfer.files[0]); }}>
      <span className="upload-icon"><Icon name="upload" size={23}/></span><strong>上传 PDF 简历</strong><span>点击或拖拽文件到这里 · 最大 20MB</span>
    </button>
    <input ref={file} type="file" accept="application/pdf,.pdf" hidden onChange={e => { if (e.target.files[0]) onUpload(e.target.files[0]); e.target.value = ''; }}/>
    {data && <div className="resume-file"><span className="file-mark"><Icon name="file"/></span><div><strong title={data.project.filename}>{data.project.filename}</strong><span>{data.resume ? '已解析 · 9 类结构化信息' : '等待解析完成'}</span></div>{data.resume && <span className="tiny-check"><Icon name="check" size={14}/></span>}</div>}
    {data?.resume && <button className="text-button resume-review" onClick={onResume}>查看与编辑简历 <Icon name="arrow" size={14}/></button>}
    {data && !data.resume && data.project.status === 'error' && <button className="text-button resume-review" disabled={busy} onClick={onRetry}>重新解析简历 <Icon name="arrow" size={14}/></button>}
    <div className="form-divider"/>
    <fieldset disabled={!data?.resume || busy}>
      <label>求职方向<input value={form.target_directions} maxLength={300} onChange={e => edit('target_directions', e.target.value)} placeholder="例如 Agent / AI 应用开发"/></label>
      <div className="form-row"><label>城市<input value={form.cities} onChange={e => edit('cities', e.target.value)} placeholder="多个城市用顿号分隔"/></label><label>工作经验<select value={form.experience_filter} onChange={e => edit('experience_filter', e.target.value)}>{experiences.map(v => <option key={v}>{v}</option>)}</select></label></div>
      <label className="employment-choice">用工偏好<select value={form.employment_type || '全职'} onChange={e => edit('employment_type', e.target.value)}><option>全职</option><option>不限</option></select></label>
      <label>搜索关键词 <span className="label-note">按顺序逐个搜索</span></label>
      <ol className="keyword-list">{form.primary_search_keywords.map((value, index) => <li key={value}>
        <span className="keyword-number">{index + 1}</span><span title={value}>{value}</span><div className="keyword-actions">
          {index > 0 && <button title="提前搜索这个关键词" aria-label={`提前搜索 ${value}`} onClick={() => { const values = [...form.primary_search_keywords]; [values[index - 1], values[index]] = [values[index], values[index - 1]]; edit('primary_search_keywords', values); }}>↑</button>}
          <button aria-label={`删除关键词 ${value}`} onClick={() => edit('primary_search_keywords', form.primary_search_keywords.filter(k => k !== value))}><Icon name="close" size={13}/></button></div>
      </li>)}</ol>
      <form className="keyword-add" onSubmit={addKeyword}><input aria-label="添加关键词" maxLength={30} value={keyword} onChange={e => setKeyword(e.target.value)} placeholder={form.primary_search_keywords.length >= 6 ? '最多 6 个关键词' : '添加关键词，按回车确认'} disabled={form.primary_search_keywords.length >= 6}/><button title="添加关键词" aria-label="添加关键词" disabled={!keyword.trim() || form.primary_search_keywords.length >= 6}>＋</button></form>
      <button className="secondary full generate-button" onClick={() => onGenerate(preferences())}><Icon name="spark"/>AI 重新生成建议</button>
      <details className="search-more"><summary>经验说明与采集数量</summary><label>工作经验说明<textarea rows={3} value={form.experience_note} onChange={e => edit('experience_note', e.target.value)} placeholder="例如：部分全职、部分实习"/></label>
        <div className="form-row"><label>每词最多<input type="number" min={1} max={20} value={limits.max_jobs_per_search} onChange={e => setLimits({ ...limits, max_jobs_per_search: Number(e.target.value) })}/></label><label>本轮最多<input type="number" min={1} max={100} value={limits.max_jobs_total} onChange={e => setLimits({ ...limits, max_jobs_total: Number(e.target.value) })}/></label></div>
        <label className="checkbox-label"><input type="checkbox" checked={limits.collect_company_details} onChange={e => setLimits({ ...limits, collect_company_details: e.target.checked })}/>补充访问公司主页</label>
      </details>
    </fieldset>
    <div className="browser-connection" title={browser.auth_saved_at ? `登录状态已保存：${new Date(browser.auth_saved_at).toLocaleString('zh-CN')}` : ''}><div><span className={`dot ${browser.status === 'ready' ? 'green' : 'gray'}`}/><span>{browser.status === 'ready' ? 'BOSS 已连接' : browser.status === 'needs_login' ? '等待 APP 扫码登录' : browser.status === 'collecting' ? 'BOSS 正在采集' : browser.status === 'connecting' ? '正在打开 BOSS' : browser.status === 'checking' ? '正在复用已有登录' : browser.status === 'needs_verification' ? '请手动完成 BOSS 验证' : 'BOSS 尚未连接'}</span></div>{browser.status === 'ready' ? <span className="saved-auth">登录已保存</span> : <button className="text-button" onClick={onConnect} disabled={busy || ['connecting', 'collecting','checking'].includes(browser.status)}>连接 BOSS</button>}</div>
    {canSearch && <button className="text-button save-search" onClick={save} disabled={busy}>{dirty || !data.project.search_confirmed ? '保存搜索条件' : '✓ 条件已保存'}</button>}
    <button className="primary full search-start" disabled={busy || !canSearch || browser.status !== 'ready'} onClick={collect}><Icon name="search"/>搜索并自动匹配<Icon name="arrow" size={16}/></button>
    <p className="footnote">采集完成后自动匹配，按匹配度排序。<br/>仅采集和分析，不投递；BOSS 窗口保留。</p>
  </aside>;
}
