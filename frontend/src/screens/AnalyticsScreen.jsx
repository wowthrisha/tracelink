import { C, mono } from '../constants/tokens.js';
import { _errMsg } from '../utils/viewer.js';
import { useToast } from '../contexts/toast.jsx';
import { label, SectionLabel, Chip, Btn, Card, Divider, Header, RiskBadge } from '../components/atoms.jsx';
import { KpiCard } from '../components/analytics/KpiCard.jsx';
import { SparkChart } from '../components/analytics/SparkChart.jsx';
import { DonutChart } from '../components/analytics/DonutChart.jsx';
import { DocAnalyticsRow } from '../components/analytics/DocAnalyticsRow.jsx';
const { useState, useEffect } = React;

export function AnalyticsScreen() {
  const toast = useToast();
  const [analyticsTab, setAnalyticsTab] = useState('overview'); // 'overview' | 'documents' | 'groups'

  const [overview, setOverview] = useState(null);
  const [docStats, setDocStats] = useState([]);
  const [groupStats, setGroupStats] = useState([]);
  const [analyticsLoading, setAnalyticsLoading] = useState(true);
  const [selectedHeatmapDoc, setSelectedHeatmapDoc] = useState(null); // {id, filename}
  const [heatmapData, setHeatmapData] = useState(null);
  const [heatmapLoading, setHeatmapLoading] = useState(false);
  const [showAllGroups, setShowAllGroups] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      window.SecureDocAPI.getAnalyticsOverview(),
      window.SecureDocAPI.getDocumentAnalytics(),
      window.SecureDocAPI.getGroupAnalytics(),
    ])
      .then(([ov, ds, gs]) => {
        if (cancelled) return;
        setOverview(ov);
        setDocStats(ds.documents || []);
        setGroupStats(gs.groups || []);
      })
      .catch(e => { if (!cancelled) toast(_errMsg(e, 'Failed to load analytics'), 'error'); })
      .finally(() => { if (!cancelled) setAnalyticsLoading(false); });
    return () => { cancelled = true; };
  }, []);

  const totalViews = overview?.total_views_today || 0;
  const activeDocs = docStats.filter(d => d.total_views > 0);
  const avgSessionSec = activeDocs.length > 0
    ? activeDocs.reduce((a, d) => a + (d.avg_time_on_page_sec || 0), 0) / activeDocs.length : 0;
  const avgSessionStr = avgSessionSec > 0
    ? `${Math.floor(avgSessionSec / 60)}m ${Math.round(avgSessionSec % 60)}s` : '—';
  const avgCompletion = activeDocs.length > 0
    ? Math.round(activeDocs.reduce((a, d) => a + (d.completion_rate_pct || 0), 0) / activeDocs.length) : 0;
  const kpis = [
    { label: 'Views Today', value: totalViews.toLocaleString(), icon: '▦', tooltip: 'Number of document page views recorded today.' },
    { label: 'Active Links', value: (overview?.active_links || 0).toString(), icon: '◫', tooltip: 'Share links that are not revoked or expired.' },
    { label: 'Avg Session', value: avgSessionStr, icon: '⏱', tooltip: 'Average time spent per page across all active documents. Documents with zero views are excluded.' },
    { label: 'Blocked Attempts', value: (overview?.blocked_attempts_today || 0).toString(), icon: '⊗', tooltip: 'DRM events today: blocked prints, copies, downloads, and right-clicks.' },
    { label: 'Active Docs', value: activeDocs.length.toString(), icon: '◈', tooltip: 'Documents with at least one view recorded.' },
    { label: 'Completion', value: avgCompletion > 0 ? `${avgCompletion}%` : '—', icon: '⊕', tooltip: 'Average completion rate — percentage of pages viewed per session, averaged across active documents.' },
  ];

  const topDocs = docStats.map(d => ({
    name: d.filename, views: d.total_views || 0, unique: d.unique_sessions || 0,
    avgTime: d.avg_time_on_page_sec > 0 ? `${Math.floor(d.avg_time_on_page_sec / 60)}m ${Math.round(d.avg_time_on_page_sec % 60)}s` : '—',
    risk: d.risk_score || 'LOW',
    group_name: d.group_name || null, group_color: d.group_color || null,
  }));

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }} className="fade-in">
      <Header screen="analytics">
        {/* Analytics tabs */}
        <div style={{ display: 'flex', gap: 2, background: C.surface2, borderRadius: 8, padding: 3 }}>
          {[['overview', 'Overview'], ['documents', 'By Document'], ['groups', 'By Group']].map(([id, lbl]) => (
            <button key={id} onClick={() => setAnalyticsTab(id)}
              style={{
                fontSize: 11, padding: '5px 12px', borderRadius: 6, border: 'none', cursor: 'pointer',
                background: analyticsTab === id ? C.surface : 'transparent',
                color: analyticsTab === id ? C.teal1 : C.textMuted,
                fontFamily: "'DM Sans',sans-serif", fontWeight: analyticsTab === id ? 600 : 400,
                transition: 'all .12s'
              }}>{lbl}</button>
          ))}
        </div>
        <Btn variant="secondary" size="sm" onClick={() => {
          let rows, filename;
          if (analyticsTab === 'documents') {
            if (!docStats.length) { toast('No document data to export', 'info'); return; }
            const header = 'Document,Group,Views,Sessions,Avg Session,Completion %,Blocked,Risk';
            rows = docStats.map(d => [
              `"${(d.filename || '').replace(/"/g, '""')}"`,
              `"${(d.group_name || '').replace(/"/g, '""')}"`,
              d.total_views || 0,
              d.unique_sessions || 0,
              d.avg_time_on_page_sec > 0 ? `${Math.floor(d.avg_time_on_page_sec / 60)}m ${Math.round(d.avg_time_on_page_sec % 60)}s` : '',
              d.completion_rate_pct || 0,
              d.blocked_attempts || 0,
              d.risk_score || 'LOW',
            ].join(','));
            filename = 'analytics_by_document.csv';
            rows.unshift(header);
          } else if (analyticsTab === 'groups') {
            if (!groupStats.length) { toast('No group data to export', 'info'); return; }
            const header = 'Group,Views,Sessions,Documents';
            rows = groupStats.map(g => [
              `"${(g.group_name || '').replace(/"/g, '""')}"`,
              g.total_views || 0,
              g.unique_sessions || 0,
              g.document_count || 0,
            ].join(','));
            filename = 'analytics_by_group.csv';
            rows.unshift(header);
          } else {
            if (!overview) { toast('No overview data to export', 'info'); return; }
            rows = [
              'Metric,Value',
              `Total Views,${overview.total_views_today || 0}`,
              `Active Links,${overview.active_links || 0}`,
              `Blocked Attempts,${overview.blocked_attempts_today || 0}`,
              `Active Documents,${docStats.filter(d => d.total_views > 0).length}`,
            ];
            filename = 'analytics_overview.csv';
          }
          const blob = new Blob([rows.join('\n')], { type: 'text/csv' });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a'); a.href = url; a.download = filename; a.click();
          URL.revokeObjectURL(url);
          toast('CSV downloaded', 'success');
        }}>
          ↓ Export CSV
        </Btn>
      </Header>

      <div style={{ flex: 1, overflow: 'auto', padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>

        {/* ── BY DOCUMENT TAB ── */}
        {analyticsTab === 'documents' && (
          <>
            <Card noPad>
              <div style={{ padding: '10px 14px', borderBottom: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <SectionLabel>Per-Document Analytics</SectionLabel>
                <Chip color={C.textMuted} bg="transparent" border={C.border}>{docStats.length} docs</Chip>
              </div>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                    {['Document', 'Group', 'Views', 'Sessions', 'Completion', 'Blocked', 'Risk', ''].map(h => (
                      <th key={h} style={{ ...label(9), padding: '8px 14px', textAlign: 'left', color: C.textDim }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {docStats.length === 0 ? (
                    <tr><td colSpan={8} style={{ padding: 24, textAlign: 'center', color: C.textMuted, fontSize: 12 }}>No documents yet</td></tr>
                  ) : docStats.map((d, i) => {
                    const isSelected = selectedHeatmapDoc?.id === d.id;
                    return (
                      <tr key={d.id} onClick={() => {
                        if (isSelected) { setSelectedHeatmapDoc(null); setHeatmapData(null); return; }
                        setSelectedHeatmapDoc({ id: d.id, filename: d.filename });
                        setHeatmapData(null);
                        setHeatmapLoading(true);
                        window.SecureDocAPI.getPageHeatmap(d.id)
                          .then(data => setHeatmapData(data))
                          .catch(() => setHeatmapData(null))
                          .finally(() => setHeatmapLoading(false));
                      }} style={{
                        borderBottom: i === docStats.length - 1 ? 'none' : `1px solid ${C.border}`,
                        background: isSelected ? 'rgba(90,200,208,0.04)' : 'transparent',
                        cursor: 'pointer', transition: 'background .1s',
                      }}>
                        <td style={{ padding: '10px 14px', fontSize: 12, color: C.textPrimary, maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{d.filename}</td>
                        <td style={{ padding: '10px 14px' }}>
                          {d.group_name ? (
                            <span style={{ fontSize: 9, padding: '2px 7px', borderRadius: 10, background: `${d.group_color || '#6366f1'}22`, color: d.group_color || '#6366f1', border: `1px solid ${d.group_color || '#6366f1'}44` }}>{d.group_name}</span>
                          ) : <span style={{ fontSize: 9, color: C.textDim }}>—</span>}
                        </td>
                        <td style={{ ...mono, padding: '10px 14px', fontSize: 11, color: C.textSecondary }}>{d.total_views}</td>
                        <td style={{ ...mono, padding: '10px 14px', fontSize: 11, color: C.textMuted }}>{d.unique_sessions}</td>
                        <td style={{ ...mono, padding: '10px 14px', fontSize: 11, color: C.textMuted }}>{d.completion_rate_pct}%</td>
                        <td style={{ ...mono, padding: '10px 14px', fontSize: 11, color: d.blocked_attempts > 0 ? C.error : C.textMuted }}>{d.blocked_attempts}</td>
                        <td style={{ padding: '10px 14px' }}><RiskBadge level={d.risk_score} /></td>
                        <td style={{ padding: '10px 14px', color: C.teal2, fontSize: 10 }}>{isSelected ? '▲ Hide' : '▦ Heatmap'}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </Card>

            {/* Page Heatmap panel — Features 3 & 4 */}
            {selectedHeatmapDoc && (
              <Card style={{ padding: 0 }}>
                <div style={{ padding: '12px 16px', borderBottom: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ fontSize: 13, color: '#5ac8d0' }}>▦</span>
                  <div>
                    <div style={{ fontSize: 12.5, fontWeight: 600, color: C.textPrimary }}>{selectedHeatmapDoc.filename}</div>
                    <div style={{ fontSize: 10, color: C.textDim, marginTop: 1 }}>Page engagement heatmap · click any row to drill in</div>
                  </div>
                  {heatmapData && (
                    <span style={{ marginLeft: 'auto', ...mono, fontSize: 10, color: C.textMuted }}>{heatmapData.total_views} total page views</span>
                  )}
                </div>

                {heatmapLoading && (
                  <div style={{ padding: 32, textAlign: 'center', color: C.textMuted, fontSize: 12 }}>Loading heatmap…</div>
                )}

                {!heatmapLoading && heatmapData && heatmapData.pages.length === 0 && (
                  <div style={{ padding: 32, textAlign: 'center', color: C.textMuted, fontSize: 12 }}>
                    No page views recorded yet for this document.
                  </div>
                )}

                {!heatmapLoading && heatmapData && heatmapData.pages.length > 0 && (
                  <div style={{ padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 5 }}>
                    {/* Top pages header */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                      <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: C.textDim }}>Most Viewed Pages</span>
                      <span style={{ ...mono, fontSize: 9, color: C.textDim }}>· {heatmapData.page_count} pages total</span>
                    </div>
                    {heatmapData.pages.slice(0, 20).map((p, i) => {
                      const maxViews = heatmapData.pages[0]?.views || 1;
                      const barPct = Math.max(2, Math.round((p.views / maxViews) * 100));
                      const heat = p.pct > 15 ? '#ff6b35' : p.pct > 8 ? '#ffd166' : '#5ac8d0';
                      return (
                        <div key={p.page} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          <div style={{ ...mono, fontSize: 10, color: C.textMuted, width: 52, flexShrink: 0, textAlign: 'right' }}>
                            {i < 3 ? '🔥' : ''} p.{p.page}
                          </div>
                          <div style={{ flex: 1, height: 16, background: 'rgba(255,255,255,0.04)', borderRadius: 3, overflow: 'hidden' }}>
                            <div style={{
                              width: `${barPct}%`, height: '100%',
                              background: `linear-gradient(90deg, ${heat}aa, ${heat})`,
                              borderRadius: 3, transition: 'width .3s ease',
                            }} />
                          </div>
                          <div style={{ ...mono, fontSize: 10, color: C.textSecondary, width: 52, flexShrink: 0 }}>
                            {p.views} view{p.views !== 1 ? 's' : ''}
                          </div>
                          <div style={{ ...mono, fontSize: 9, color: C.textDim, width: 48, flexShrink: 0 }}>
                            {p.avg_time_sec > 0 ? `${p.avg_time_sec}s avg` : ''}
                          </div>
                        </div>
                      );
                    })}
                    {heatmapData.pages.length > 20 && (
                      <div style={{ fontSize: 10, color: C.textDim, textAlign: 'center', paddingTop: 4 }}>
                        Showing top 20 of {heatmapData.pages.length} pages with views
                      </div>
                    )}
                  </div>
                )}
              </Card>
            )}
          </>
        )}

        {/* ── BY GROUP TAB ── */}
        {analyticsTab === 'groups' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {groupStats.length === 0 ? (
              <Card style={{ padding: 32, textAlign: 'center' }}>
                <div style={{ fontSize: 13, color: C.textMuted, marginBottom: 8 }}>No groups created yet</div>
                <div style={{ fontSize: 11, color: C.textDim }}>Create groups in the Documents screen to organize your files</div>
              </Card>
            ) : (
              <>
                {/* Group KPI cards */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 10 }}>
                  {groupStats.map(g => (
                    <Card key={g.group_id} style={{ padding: '14px 16px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                        <div style={{ width: 10, height: 10, borderRadius: '50%', background: g.group_color, flexShrink: 0 }} />
                        <div style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{g.group_name}</div>
                        <RiskBadge level={g.risk_score} />
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                        {[
                          { l: 'Docs', v: g.document_count },
                          { l: 'Views', v: g.total_views },
                          { l: 'Sessions', v: g.unique_sessions },
                          { l: 'Active Links', v: g.active_links },
                          { l: 'Blocked', v: g.blocked_attempts, warn: g.blocked_attempts > 0 },
                        ].map(it => (
                          <div key={it.l}>
                            <div style={{ fontSize: 8, color: C.textDim, textTransform: 'uppercase', letterSpacing: 1 }}>{it.l}</div>
                            <div style={{ ...mono, fontSize: 18, fontWeight: 700, color: it.warn ? C.error : C.textPrimary }}>{it.v}</div>
                          </div>
                        ))}
                      </div>
                    </Card>
                  ))}
                </div>
                {/* Group comparison table */}
                <Card noPad>
                  <div style={{ padding: '10px 14px', borderBottom: `1px solid ${C.border}` }}>
                    <SectionLabel>Group Comparison</SectionLabel>
                  </div>
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                        {['Group', 'Docs', 'Total Views', 'Sessions', 'Active Links', 'Blocked', 'Risk'].map(h => (
                          <th key={h} style={{ ...label(9), padding: '8px 14px', textAlign: 'left', color: C.textDim }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {groupStats.map((g, i) => (
                        <tr key={g.group_id} style={{ borderBottom: i === groupStats.length - 1 ? 'none' : `1px solid ${C.border}` }}>
                          <td style={{ padding: '10px 14px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                              <div style={{ width: 8, height: 8, borderRadius: '50%', background: g.group_color, flexShrink: 0 }} />
                              <span style={{ fontSize: 12, fontWeight: 600, color: C.textPrimary }}>{g.group_name}</span>
                            </div>
                          </td>
                          <td style={{ ...mono, padding: '10px 14px', fontSize: 11, color: C.textSecondary }}>{g.document_count}</td>
                          <td style={{ ...mono, padding: '10px 14px', fontSize: 11, color: C.textSecondary }}>{g.total_views}</td>
                          <td style={{ ...mono, padding: '10px 14px', fontSize: 11, color: C.textMuted }}>{g.unique_sessions}</td>
                          <td style={{ ...mono, padding: '10px 14px', fontSize: 11, color: C.textMuted }}>{g.active_links}</td>
                          <td style={{ ...mono, padding: '10px 14px', fontSize: 11, color: g.blocked_attempts > 0 ? C.error : C.textMuted }}>{g.blocked_attempts}</td>
                          <td style={{ padding: '10px 14px' }}><RiskBadge level={g.risk_score} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </Card>
              </>
            )}
          </div>
        )}

        {/* ── OVERVIEW TAB ── */}
        {analyticsTab === 'overview' && <>

          {/* KPI row */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6,1fr)', gap: 10 }}>
            {kpis.map(k => <KpiCard key={k.label} k={k} />)}
          </div>

          {/* Charts */}
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 12 }}>
            <Card>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
                <div>
                  <SectionLabel>Views Over Time</SectionLabel>
                  <div style={{ ...mono, fontSize: 9, color: C.textDim, marginTop: 3 }}>
                    Daily view count · last 7 days
                  </div>
                </div>
                <div style={{ ...mono, fontSize: 22, fontWeight: 700, letterSpacing: '-1.5px', color: C.teal1 }}>{(overview?.views_last_7_days || []).reduce((a, d) => a + d.count, 0).toLocaleString()}</div>
              </div>
              <SparkChart range="7d" sparkData={overview?.views_last_7_days} />
            </Card>
            <Card>
              <SectionLabel style={{ marginBottom: 14 }}>Access Outcomes</SectionLabel>
              <DonutChart overview={overview} />
              <Divider style={{ margin: '12px 0' }} />
              <SectionLabel style={{ marginBottom: 8 }}>Top Documents</SectionLabel>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {(() => {
                  const top3 = [...docStats].sort((a, b) => (b.total_views || 0) - (a.total_views || 0)).slice(0, 3);
                  const topTotal = top3.reduce((s, d) => s + (d.total_views || 0), 0);
                  if (top3.length === 0) return <div style={{ fontSize: 11, color: C.textMuted }}>No views yet</div>;
                  return top3.map(d => {
                    const pct = topTotal > 0 ? Math.round((d.total_views / topTotal) * 100) : 0;
                    return (
                      <div key={d.id}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                          <span style={{ ...mono, fontSize: 10, color: C.textSecondary, overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '70%' }}>{d.filename}</span>
                          <span style={{ ...mono, fontSize: 10, color: C.textMuted }}>{d.total_views}</span>
                        </div>
                        <div style={{ height: 3, background: 'rgba(90,200,208,0.1)', borderRadius: 2 }}>
                          <div style={{
                            height: '100%', width: `${pct}%`,
                            background: `linear-gradient(90deg, ${C.teal4}, ${C.teal1})`, borderRadius: 2
                          }} />
                        </div>
                      </div>
                    );
                  });
                })()}
              </div>
            </Card>
          </div>

          {/* Table + security events */}
          <div style={{ display: 'grid', gridTemplateColumns: '3fr 1fr', gap: 12 }}>
            <Card noPad>
              <div style={{
                padding: '10px 14px', borderBottom: `1px solid ${C.border}`,
                display: 'flex', alignItems: 'center', justifyContent: 'space-between'
              }}>
                <SectionLabel>Document Performance</SectionLabel>
                <Chip color={C.textMuted} bg="transparent" border={C.border}>{topDocs.length} docs</Chip>
              </div>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                    {['Document', 'Group', 'Views', 'Unique', 'Avg Time', 'Risk'].map(h => (
                      <th key={h} style={{ ...label(9), padding: '8px 14px', textAlign: 'left', color: C.textDim }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {topDocs.map((d, i) => <DocAnalyticsRow key={d.name} doc={d} isLast={i === topDocs.length - 1} />)}
                </tbody>
              </table>
            </Card>

            <Card>
              <SectionLabel style={{ marginBottom: 10 }}>Groups at a Glance</SectionLabel>
              {groupStats.length === 0 ? (
                <div style={{ fontSize: 11, color: C.textMuted, padding: '8px 0' }}>No groups yet</div>
              ) : (showAllGroups ? groupStats : groupStats.slice(0, 5)).map(g => (
                <div key={g.group_id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <div style={{ width: 7, height: 7, borderRadius: '50%', background: g.group_color, flexShrink: 0 }} />
                    <span style={{ fontSize: 10, color: C.textSecondary, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 90 }}>{g.group_name}</span>
                  </div>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <span style={{ ...mono, fontSize: 10, color: C.textMuted }}>{g.total_views}v</span>
                    <RiskBadge level={g.risk_score} />
                  </div>
                </div>
              ))}
              {groupStats.length > 5 && (
                <button onClick={() => setShowAllGroups(v => !v)}
                  style={{
                    fontSize: 10, color: C.teal3, background: 'none', border: 'none',
                    cursor: 'pointer', padding: '2px 0', fontFamily: "'DM Sans', sans-serif"
                  }}>
                  {showAllGroups ? 'Show fewer' : `Show all ${groupStats.length}`}
                </button>
              )}
              <Divider style={{ margin: '12px 0' }} />
              <SectionLabel style={{ marginBottom: 8 }}>Security Activity</SectionLabel>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: 10, color: C.textSecondary }}>Blocked today</span>
                  <span style={{ ...mono, fontSize: 10, color: overview?.blocked_attempts_today > 0 ? C.error : C.success }}>{overview?.blocked_attempts_today || 0}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: 10, color: C.textSecondary }}>Active links</span>
                  <span style={{ ...mono, fontSize: 10, color: C.teal1 }}>{overview?.active_links || 0}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: 10, color: C.textSecondary }}>Expiring soon</span>
                  <span style={{ ...mono, fontSize: 10, color: overview?.expiring_soon_count > 0 ? C.warning : C.textMuted }}>{overview?.expiring_soon_count || 0}</span>
                </div>
              </div>
            </Card>
          </div>
        </>}
      </div>
    </div>
  );
}
