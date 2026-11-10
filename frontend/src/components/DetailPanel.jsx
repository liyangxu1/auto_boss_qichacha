import { metaText } from '../api';
import { useState } from 'react';
import Icon from './Icon';
import { Score } from './JobsPanel';
function KeyValues({ rows }) { return <dl className="key-values">{rows.filter(([, value]) => value).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{typeof value === 'object' ? JSON.stringify(value) : value}</dd></div>)}</dl>; }
export default function DetailPanel({ job }) {
  const [tab, setTab] = useState('职位信息');
  return <aside className="panel detail-panel"><div className="panel-heading"><h2>岗位详情</h2><Icon name="briefcase" size={17}/></div>
    <div className="detail-tabs" role="tablist" aria-label="岗位详情内容">{['职位信息', '匹配分析', '公司信息'].map(t => <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)} className={tab === t ? 'selected' : ''}>{t}</button>)}</div>
    {!job ? <div className="empty-state compact"><Icon name="file" size={30}/><p>选择一个岗位，查看职位详情<br/>和匹配依据</p></div> : <>
      <div className="detail-body">
        {tab === '职位信息' && <><h3 className="detail-title">{job.title}</h3><p className="salary detail-salary">{job.salary || '薪资未公开'}</p><p className="job-meta">{metaText(job)}</p>
          <div className="section-rule"/><h4>职位描述</h4><p className="description">{job.description || '当前页面未公开完整岗位描述。可在 BOSS 登录后重新采集。'}</p>
          {!!job.benefits?.length && <><h4>福利待遇</h4><div className="tags">{job.benefits.map((b, i) => <span key={i}>{b}</span>)}</div></>}
          <div className="section-rule"/><h4>公司概况</h4><CompanySummary company={job.company}/>
          <p className="source-note">{job.collected_at ? `采集于 ${new Date(job.collected_at).toLocaleString('zh-CN')}` : '来自 BOSS 页面公开信息'}{job.access_limited ? ' · 资料受限' : ''}</p>
        </>}
        {tab === '匹配分析' && <>{!job.match ? <div className="empty-state compact"><Icon name="spark" size={30}/><h3>尚未进行匹配</h3><p>点击“开始 AI 匹配”，按评分规则逐项分析。</p></div> : <><div className="match-overview"><Score match={job.match} large/><div><strong>信息完整度 {job.match.coverage}%</strong><p>{job.match.rankable ? '已达到排序所需完整度' : '信息不足，暂不纳入优先排序'}</p></div></div><p className="match-summary">{job.match.summary}</p><p className="source-note">分数表示当前规则下的适配程度，不代表录用概率。</p>
          <div className="dimension-list">{job.match.dimensions.map(d => <details className="dimension" key={d.id} open={d.status === 'unknown'}><summary><span>{d.name}<small>权重 {d.weight}%</small></span><b className={d.score == null ? 'muted' : ''}>{d.score == null ? '待确认' : `${d.score} / 5`}</b></summary>
            <p><strong>岗位要求</strong>{d.requirement || '未明确'}</p><p>{d.explanation}</p>{d.evidence.map((e, i) => <blockquote key={i}>{e.quote}<small>简历 {e.path}</small></blockquote>)}{!!d.gaps.length && <p className="gap-text">能力差距：{d.gaps.join('；')}</p>}{!!d.uncertainties?.length && <p className="gap-text">需要确认：{d.uncertainties.join('；')}</p>}</details>)}</div>
        </>}</>}
        {tab === '公司信息' && <><h3 className="detail-title">{job.company?.name || '公司未公开'}</h3><CompanySummary company={job.company}/>{job.company?.anonymous && <p className="notice">该岗位为匿名招聘，不能据此确定雇主真实身份。</p>}<div className="section-rule"/><h4>公司介绍</h4><p className="description">{job.company?.description || '当前岗位没有公开公司介绍，可尝试开启“补充访问公司主页”后采集。'}</p><KeyValues rows={[["地址", job.company?.address], ["官网", job.company?.website]]}/>{job.company?.business_info && Object.keys(job.company.business_info).length > 0 && <><h4>工商信息</h4><KeyValues rows={Object.entries(job.company.business_info)}/></>}</>}
      </div><div className="detail-footer"><a className="secondary full" href={job.url} target="_blank" rel="noreferrer">在 BOSS 查看<Icon name="external" size={15}/></a></div>
    </>}
  </aside>;
}
function CompanySummary({ company }) { return <KeyValues rows={[["公司", company?.name || '未公开'], ["行业", company?.industry], ["融资", company?.financing], ["规模", company?.size]]}/>; }
