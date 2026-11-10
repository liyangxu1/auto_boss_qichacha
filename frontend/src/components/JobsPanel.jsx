import { metaText } from '../api';
import { useMemo, useState } from 'react';
import Icon from './Icon';
export function Score({ match, large = false }) {
  if (!match) return <span className={`score pending ${large ? 'large' : ''}`}>待匹配</span>;
  return <div className={`score ${match.rankable ? '' : 'uncertain'} ${large ? 'large' : ''}`}><strong>{match.rankable ? match.score : '—'}<small>{match.rankable ? '%' : ''}</small></strong><span>{match.rankable ? '匹配度' : '待确认'}</span></div>;
}
export default function JobsPanel({ jobs, catalog, showExcluded, onShowExcluded, selected, onSelect, onMatch, busy, projectId }) {
  const [query, setQuery] = useState('');
  const [tab, setTab] = useState('全部岗位');
  const [sort, setSort] = useState('score');
  const filtered = useMemo(() => {
    const result = jobs.filter(job => `${job.title} ${job.company?.name || ''} ${job.tags?.join(' ') || ''}`.toLowerCase().includes(query.toLowerCase()))
      .filter(job => tab === '全部岗位' || (tab === '已匹配' ? job.match : !job.match && !job.excluded));
    if (sort === 'score') result.sort((a, b) => Number(a.excluded) - Number(b.excluded) || Number(Boolean(b.match?.rankable)) - Number(Boolean(a.match?.rankable)) || (b.match?.score ?? -1) - (a.match?.score ?? -1));
    return result;
  }, [jobs, query, tab, sort]);
  const matched = jobs.filter(j => j.match).length;
  const pending = jobs.filter(j => !j.match && !j.excluded).length;
  return <section className="panel jobs-panel">
    <div className="panel-heading"><h2>岗位列表 <span className="count">{jobs.length}</span></h2><a className={`icon-button ${!projectId ? 'disabled' : ''}`} href={projectId ? `/api/projects/${projectId}/export?include_excluded=${showExcluded}` : undefined} download aria-label="导出岗位 JSON" title="导出岗位 JSON"><Icon name="export"/></a></div>
    <div className="list-toolbar"><div className="search-input"><Icon name="search" size={16}/><input value={query} onChange={e => setQuery(e.target.value)} placeholder="搜索职位、公司或技能" aria-label="筛选岗位列表"/></div><select value={sort} onChange={e => setSort(e.target.value)} aria-label="岗位排序"><option value="score">匹配度从高到低</option><option value="original">采集顺序</option></select></div>
    <div className="catalog-note"><strong>历史岗位累计保留 · 按岗位去重</strong><span>累计 {catalog?.total || 0} 个 · 可匹配 {catalog?.eligible || 0} 个 · 已过滤 {catalog?.excluded || 0} 个</span><label className="checkbox-label"><input type="checkbox" checked={showExcluded} onChange={e => onShowExcluded(e.target.checked)}/>显示已过滤岗位</label><small>兼职、实习默认隐藏且不参与匹配；未标注用工类型的岗位需核实。</small></div>
    <div className="list-tabs" role="tablist" aria-label="岗位匹配状态">{['全部岗位', '已匹配', '待匹配'].map(t => <button key={t} role="tab" aria-selected={tab === t} className={tab === t ? 'selected' : ''} onClick={() => setTab(t)}>{t}<span>{t === '全部岗位' ? jobs.length : t === '已匹配' ? matched : pending}</span></button>)}</div>
    <div className="job-items">
      {filtered.map(job => <button className={`job-card ${selected?.id === job.id ? 'selected' : ''}`} key={job.id} onClick={() => onSelect(job.id)}>
        <div className="job-card-top"><h3>{job.title}</h3>{job.excluded ? <span className="score pending">不参与匹配</span> : <Score match={job.match}/>}</div>
        <p className="salary">{job.salary || '薪资未公开'}</p><p className="job-meta">{metaText(job)}</p>
        <div className="tags">{job.excluded && <span className="warning-tag">已过滤 · {job.exclusion_reason}</span>}{(job.tags || []).filter(t => ![job.experience, job.education].includes(t)).slice(0, 4).map((t, i) => <span key={i}>{t}</span>)}{job.access_limited && <span className="warning-tag">资料受限</span>}</div>
        <div className="company-line"><span className="company-avatar"><Icon name="building" size={16}/></span><div><strong>{job.company?.name || job.company_name || '公司未公开'}</strong><span>{[job.company?.industry, job.company?.financing, job.company?.size].filter(Boolean).join(' · ') || '公司资料待补充'}</span></div></div>
        {job.match && <p className="coverage-line">信息完整度 {job.match.coverage}%{!job.match.rankable ? ' · 不纳入优先排序' : ''}</p>}
      </button>)}
      {!filtered.length && <div className="empty-state"><span className="empty-symbol"><Icon name={jobs.length ? 'search' : 'briefcase'} size={30}/></span><h3>{jobs.length ? '没有符合条件的岗位' : '把适合你的岗位，收进这里'}</h3><p>{jobs.length ? '调整筛选关键词或切换标签再看看。' : '上传简历、确认搜索条件，再连接 BOSS 开始采集。'}</p></div>}
    </div>
    <div className="list-footer"><span>{matched ? `${matched} 个已匹配` : '从简历出发，逐项比较真实岗位'}</span><button className="primary" onClick={onMatch} disabled={!jobs.some(j => !j.excluded) || busy}><Icon name="spark" size={16}/>{pending ? '匹配待处理岗位' : '更新 AI 匹配'}</button></div>
  </section>;
}
