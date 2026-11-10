import { useCallback, useEffect, useState } from 'react';
import { api, json, activeStates } from './api';
import Icon from './components/Icon';
import SearchPanel from './components/SearchPanel';
import JobsPanel from './components/JobsPanel';
import DetailPanel from './components/DetailPanel';
import { ResumeEditor, RulesEditor } from './components/Editors';

export default function App() {
  const [state, setState] = useState(null), [projectId, setProjectId] = useState(null), [data, setData] = useState(null);
  const [selectedId, setSelectedId] = useState(null), [modal, setModal] = useState(null), [notice, setNotice] = useState(null);
  const [submitting, setSubmitting] = useState(false), [unavailable, setUnavailable] = useState(false);
  const [showExcluded, setShowExcluded] = useState(false);
  const closeModal = useCallback(() => setModal(null), []);
  const refresh = useCallback(async () => {
    const [nextState, nextProject] = await Promise.all([api('/state'), projectId ? api(`/projects/${projectId}`) : null]);
    setState(nextState); setUnavailable(false);
    if (!projectId && nextState.projects[0]) setProjectId(nextState.projects[0].id);
    if (nextProject) setData(nextProject);
  }, [projectId]);
  useEffect(() => {
    let stopped = false, timer;
    async function poll() { try { if (!stopped) await refresh(); } catch { if (!stopped) setUnavailable(true); } if (!stopped) timer = setTimeout(poll, 2000); }
    poll(); return () => { stopped = true; clearTimeout(timer); };
  }, [refresh]);
  useEffect(() => { setSelectedId(null); setData(null); setShowExcluded(false); }, [projectId]);
  const tasks = data?.tasks || [], activeTask = tasks.find(t => activeStates.has(t.status)), latestTask = activeTask || tasks[0];
  const taskFailed = ['error', 'partial', 'interrupted'].includes(latestTask?.status);
  const busy = submitting || Boolean(activeTask), jobs = (data?.jobs || []).filter(j => showExcluded || !j.excluded);
  const selected = jobs.find(j => j.id === selectedId) || [...jobs].sort((a,b) => Number(Boolean(b.match?.rankable)) - Number(Boolean(a.match?.rankable)) || (b.match?.score ?? -1) - (a.match?.score ?? -1))[0];
  const browser = state?.browser || { status: 'disconnected' };
  const step = activeTask?.kind === 'parse' ? 0 : activeTask?.kind === 'keywords' ? 1 : activeTask?.kind === 'collect' ? 2 : activeTask?.kind === 'match' || jobs.some(j => j.match) ? 3 : data?.search ? 1 : 0;
  async function action(fn, success) {
    setSubmitting(true); setNotice(null);
    try { await fn(); if (success) setNotice({ message: success, kind: 'success' }); await refresh(); return true; }
    catch (error) { setNotice({ message: error.message, kind: 'error' }); return false; }
    finally { setSubmitting(false); }
  }
  async function upload(file) {
    if (file.size > 20 * 1024 * 1024) { setNotice({ kind:'error', message:'PDF 不能超过20MB。' }); return; }
    const form = new FormData(); form.append('file', file);
    await action(async () => { const result = await api('/resumes', { method:'POST', body:form }); setProjectId(result.project_id); }, '已上传，正在后台解析简历');
  }
  const saveSearch = value => action(() => api(`/projects/${projectId}/search`, json('PUT', value)), '搜索条件已保存');
  const control = type => action(() => api(`/projects/${projectId}/collection-control`, json('POST', { action:type })), '已请求，完成当前岗位后生效');
  return <>
    <header className="topbar"><a className="brand" href="/" aria-label="AutoBOSS 首页"><span className="brand-mark">A</span>AutoBOSS</a><span className="topbar-title">求职工作台</span><div className="topbar-actions"><button className="text-button rules-button" disabled={!data || busy} onClick={() => setModal('rules')}><Icon name="settings"/>评分规则</button><span className="local-badge"><span className="dot green"/>本地工作台</span></div></header>
    <main className="workspace"><section className="hero"><div><p className="eyebrow">YOUR NEXT CHAPTER</p><h1>让下一份工作，更适合你。</h1><p>从一份简历开始，把搜索、筛选与匹配连在一起。</p></div><div className="project-switch">{state?.projects.length > 1 && <label>当前简历<select value={projectId || ''} onChange={e => { setProjectId(e.target.value); setNotice(null); }}>{state.projects.map(p => <option key={p.id} value={p.id}>{p.filename} · {new Date(p.created_at).toLocaleString('zh-CN', { month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit' })}</option>)}</select></label>}<span className="model-badge"><Icon name="spark" size={14}/>{state?.model.configured ? state.model.name : '模型尚未配置'}</span></div></section>
      <div className="workflow-bar"><ol>{['上传简历','调整搜索','采集岗位','匹配排序'].map((title,index) => <li key={title} className={index <= step ? 'current' : ''}><span>{index < step ? <Icon name="check" size={13}/> : `0${index+1}`}</span>{title}{index < 3 && <i/>}</li>)}</ol><div className="workflow-status"><span className={`dot ${activeTask ? 'pulse' : 'green'}`}/>{activeTask ? activeTask.status === 'paused' ? '已暂停' : '任务执行中' : '准备就绪'}{activeTask?.kind === 'collect' && <><button className="text-button" onClick={() => control(activeTask.status === 'paused' ? 'resume' : 'pause')}><Icon name="pause" size={14}/>{activeTask.status === 'paused' ? '继续采集' : '暂停采集'}</button><button className="text-button" onClick={() => control('cancel')}>停止</button></>}</div></div>
      {(notice || unavailable) && <div className={`notice ${unavailable || notice?.kind === 'error' ? 'notice-error' : ''}`} role="alert"><span>{unavailable ? '暂时无法连接本地服务，正在重连。请确认服务仍在运行。' : notice.message}</span>{!unavailable && <button className="icon-button" aria-label="关闭提示" onClick={() => setNotice(null)}><Icon name="close" size={15}/></button>}</div>}
      {latestTask && <div className={`task-strip ${taskFailed ? 'error-text' : ''}`} aria-live="polite"><span className={activeTask ? 'spinner' : ''}>{!activeTask && <Icon name={taskFailed ? 'close' : 'check'} size={15}/>}</span><span>{latestTask.message}</span>{latestTask.total > 0 && <span className="task-count">{latestTask.current} / {latestTask.total}</span>}</div>}
      <div className="workbench-grid"><SearchPanel data={data} busy={busy} browser={browser} onUpload={upload} onResume={() => setModal('resume')}
        onRetry={() => action(() => api(`/projects/${projectId}/parse`,{method:'POST'}))}
        onConnect={() => action(() => api('/browser/connect',json('POST',{project_id:projectId})), '正在复用已保存的 BOSS 登录，只有会话失效时才需扫码')}
        onSave={saveSearch} onGenerate={value => action(() => api(`/projects/${projectId}/keywords`,json('POST',value)), '已启动搜索建议生成任务')}
        onCollect={limits => action(() => api(`/projects/${projectId}/collect`,json('POST',limits)))}/>
        <JobsPanel jobs={jobs} catalog={data?.catalog} showExcluded={showExcluded} onShowExcluded={setShowExcluded} selected={selected} onSelect={setSelectedId} busy={busy || !data?.resume} projectId={projectId} onMatch={() => action(() => api(`/projects/${projectId}/match`,{method:'POST'}))}/><DetailPanel job={selected}/></div>
      <footer className="workspace-footer"><span>AutoBOSS · 让求职更有方向</span><span>简历与岗位保存在本机 · AI 分析使用已配置的模型服务</span></footer>
    </main>
    {modal === 'rules' && data && <RulesEditor value={data.rules} defaults={state.defaults} onClose={closeModal} saving={submitting} onSave={value => action(async () => { const result = await api(`/projects/${projectId}/rules`,json('PUT',value)); setNotice({kind:'success',message:result.reweighted ? `规则已保存，已重算 ${result.reweighted} 个岗位` : '规则已保存，未分析岗位请开始 AI 匹配'}); })}/>}
    {modal === 'resume' && data && <ResumeEditor data={data} onClose={closeModal} saving={busy} onSave={value => action(() => api(`/projects/${projectId}/resume`,json('PUT',value)), '简历已保存，请重新生成或确认搜索条件')}/>}
  </>;
}
