import { useState } from 'react';
import Modal from './Modal';
import Icon from './Icon';
export function RulesEditor({ value, defaults, onSave, onClose, saving }) {
  const [rules, setRules] = useState(structuredClone(value));
  const [error, setError] = useState('');
  const total = rules.dimensions.reduce((sum, d) => sum + Number(d.weight || 0), 0);
  function edit(index, key, value) { setRules(old => ({ ...old, dimensions: old.dimensions.map((d, i) => i === index ? { ...d, [key]: value } : d) })); }
  async function save() {
    if (Math.abs(total - 100) > .01) { setError('权重合计需要为100%。'); return; }
    if (await onSave(rules)) onClose();
  }
  return <Modal title="评分规则" subtitle="设定比较维度，让每一分都有依据。修改后需重新匹配。" onClose={onClose} wide footer={<><button className="text-button restore" onClick={() => { setRules(structuredClone(defaults)); setError(''); }}>恢复默认</button><span className={`weight-total ${Math.abs(total - 100) > .01 ? 'error-text' : ''}`}>权重合计 <b>{total}%</b></span><button className="secondary" onClick={onClose}>取消</button><button className="primary" disabled={saving} onClick={save}>保存规则</button></>}>
    <div className="rules-labels"><span>匹配维度</span><span>权重</span><span>评分要点</span></div><div className="rules-rows">{rules.dimensions.map((d, index) => <div className="rules-row" key={d.id}><input aria-label={`维度${index + 1}名称`} value={d.name} maxLength={30} onChange={e => edit(index, 'name', e.target.value)}/><div className="weight-input"><input type="number" aria-label={`${d.name}权重`} value={d.weight} min={0} max={100} onChange={e => edit(index, 'weight', Number(e.target.value))}/><span>%</span></div><textarea aria-label={`${d.name}评分要点`} value={d.rubric} rows={2} maxLength={1500} onChange={e => edit(index, 'rubric', e.target.value)}/></div>)}</div>
    <label className="prompt-label"><Icon name="spark" size={17}/>匹配提示词<textarea value={rules.prompt} rows={6} maxLength={12000} onChange={e => setRules({ ...rules, prompt: e.target.value })}/></label><div className="coverage-setting"><label>最低信息完整度 <input type="number" min={0} max={100} value={rules.minimum_coverage} onChange={e => setRules({ ...rules, minimum_coverage: Number(e.target.value) })}/>%</label><p>未达到该比例的岗位保留分析，标记待确认，排在信息充分的岗位之后。</p></div>{error && <p className="error-text" role="alert">{error}</p>}
  </Modal>;
}
export function ResumeEditor({ data, onSave, onClose, saving }) {
  const [text, setText] = useState(JSON.stringify(data.resume, null, 2));
  const [error, setError] = useState('');
  const [mode, setMode] = useState('预览');
  async function save() { let value; try { value = JSON.parse(text); } catch { setError('JSON 格式有误，请检查逗号和引号。'); return; } if (await onSave(value)) onClose(); }
  const fieldNames = { identity: '基本信息', intent: '求职意向', summary: '个人概述', employment: '工作经历', projects: '项目经历', skills: '技能', education: '教育经历', certifications: '证书', other: '其他' };
  const labels = { name:'名称', role:'职位', company:'公司', start_date:'开始', end_date:'结束', degree:'学历', major:'专业', school:'学校', phone:'电话', email:'邮箱', location:'现居地', age:'年龄', gender:'性别', links:'链接', target_role:'期望岗位', expected_cities:'期望城市', declared_experience:'声明经验', expected_salary:'期望薪资', availability:'到岗时间', employment_type:'用工类型', text:'内容', title:'主题', content:'内容', technologies:'技术', models:'模型', datasets:'数据', background:'项目背景', goals:'目标', technical_approach:'技术方案', evaluation:'评估', deployment:'部署', achievements:'成果', responsibilities:'职责', category:'类别', stated_proficiency:'熟练度', description:'说明', metrics:'量化指标', value:'数值', baseline:'基线', unit:'单位', sample_size:'样本量', evaluation_method:'评估方法', context:'上下文', details:'说明', level:'级别', obtained_at:'获得时间' };
  const categories = { language:'编程语言', framework:'框架', model:'模型', data:'数据', method:'技术方法', platform:'平台', deployment:'部署', tool:'工具', business:'业务', other:'其他', data_size:'数据规模', evaluation:'评估指标', latency:'延迟', throughput:'吞吐量' };
  function hasContent(value) {
    if (value == null || value === '') return false;
    if (Array.isArray(value)) return value.some(hasContent);
    if (typeof value === 'object') return Object.values(value).some(hasContent);
    return true;
  }
  function render(value) {
    if (!hasContent(value)) return null;
    if (Array.isArray(value)) return value.map((v, i) => hasContent(v) && <div className="resume-entry" key={i}>{render(v)}</div>);
    if (typeof value === 'object') return Object.entries(value).filter(([key,v]) => hasContent(v) && !['evidence','evidence_ids','source_blocks'].includes(key)).map(([key,v]) => <div className="resume-value" key={key}><span>{labels[key] || key}</span><div>{key === 'category' ? categories[v] || v : render(v)}</div></div>);
    return <span>{String(value)}</span>;
  }
  return <Modal title="简历信息" subtitle="保留约定的9类字段。修正内容后，搜索条件和匹配结果需要重新确认。" onClose={onClose} wide footer={<><span className="restore">{data.has_pdf && <a className="text-button" href={`/api/projects/${data.project.id}/pdf`} target="_blank" rel="noreferrer">查看原 PDF <Icon name="external" size={14}/></a>}</span><button className="secondary" onClick={onClose}>取消</button><button className="primary" onClick={save} disabled={saving}>保存简历</button></>}>
    <div className="editor-tabs">{['预览', '编辑 JSON'].map(m => <button className={mode === m ? 'selected' : ''} key={m} onClick={() => setMode(m)}>{m}</button>)}</div>
    {mode === '编辑 JSON' ? <textarea className="json-editor" aria-label="简历 JSON" value={text} onChange={e => { setText(e.target.value); setError(''); }} spellCheck={false}/> : <div className="resume-preview">{Object.entries(data.resume).map(([key, value]) => <section key={key}><h3>{fieldNames[key]}</h3>{Array.isArray(value) && !value.length ? <p className="muted">未提供</p> : render(value)}</section>)}</div>}
    {error && <p className="error-text" role="alert">{error}</p>}
  </Modal>;
}
