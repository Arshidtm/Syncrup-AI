'use client';
import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Sidebar from '../../components/Sidebar';
import { api } from '../../lib/api';

// ─── Repo Canvas Component ────────────────────────────────────────────────────
function RepoCanvas({ repos, connections, projectId, onConnectionCreated }) {
    const canvasRef = useRef(null);
    const [positions, setPositions] = useState({});
    const [dragging, setDragging] = useState(null);
    const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
    const [selected, setSelected] = useState(null);
    const [connecting, setConnecting] = useState(false);

    // Initialize positions for repos
    useEffect(() => {
        const newPos = {};
        repos.forEach((repo, i) => {
            if (!positions[repo.id]) {
                const cols = 3;
                const col = i % cols;
                const row = Math.floor(i / cols);
                newPos[repo.id] = { x: 60 + col * 220, y: 60 + row * 120 };
            }
        });
        if (Object.keys(newPos).length > 0) {
            setPositions(prev => ({ ...prev, ...newPos }));
        }
    }, [repos]);

    const handleMouseDown = (e, repoId) => {
        if (connecting) {
            // In connecting mode, clicking a second block creates a connection
            if (selected && selected !== repoId) {
                api.createConnection(projectId, {
                    source_repo_id: selected,
                    target_repo_id: repoId,
                }).then(() => {
                    onConnectionCreated();
                    setConnecting(false);
                    setSelected(null);
                }).catch(err => alert(err.message));
            }
            return;
        }
        const rect = e.currentTarget.getBoundingClientRect();
        setDragging(repoId);
        setDragOffset({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    };

    const handleMouseMove = useCallback((e) => {
        if (!dragging || !canvasRef.current) return;
        const canvasRect = canvasRef.current.getBoundingClientRect();
        setPositions(prev => ({
            ...prev,
            [dragging]: {
                x: e.clientX - canvasRect.left - dragOffset.x,
                y: e.clientY - canvasRect.top - dragOffset.y,
            },
        }));
    }, [dragging, dragOffset]);

    const handleMouseUp = useCallback(() => {
        setDragging(null);
    }, []);

    useEffect(() => {
        window.addEventListener('mousemove', handleMouseMove);
        window.addEventListener('mouseup', handleMouseUp);
        return () => {
            window.removeEventListener('mousemove', handleMouseMove);
            window.removeEventListener('mouseup', handleMouseUp);
        };
    }, [handleMouseMove, handleMouseUp]);

    function startConnecting(repoId) {
        setSelected(repoId);
        setConnecting(true);
    }

    const statusColors = {
        ready: 'var(--success)',
        processing: 'var(--warning)',
        pending: 'var(--text-muted)',
        error: 'var(--danger)',
    };

    return (
        <div>
            <div className="flex items-center justify-between mb-16">
                <div className="flex items-center gap-12">
                    <h3 className="card-title">Repository Canvas</h3>
                    {connecting && (
                        <span className="badge badge-info">Click a target repo to connect</span>
                    )}
                </div>
                {connecting && (
                    <button className="btn btn-secondary btn-sm" onClick={() => { setConnecting(false); setSelected(null); }}>
                        Cancel
                    </button>
                )}
            </div>

            <div className="repo-canvas" ref={canvasRef}>
                {/* Connection Lines */}
                <svg className="connection-svg">
                    {connections.map((conn) => {
                        const sp = positions[conn.source_repo_id];
                        const tp = positions[conn.target_repo_id];
                        if (!sp || !tp) return null;
                        return (
                            <line
                                key={conn.id}
                                className="connection-line"
                                x1={sp.x + 90} y1={sp.y + 30}
                                x2={tp.x + 90} y2={tp.y + 30}
                                markerEnd="url(#arrowhead)"
                            />
                        );
                    })}
                    <defs>
                        <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
                            <polygon points="0 0, 10 3.5, 0 7" fill="var(--accent)" opacity="0.6" />
                        </marker>
                    </defs>
                </svg>

                {/* Repo Blocks */}
                {repos.map((repo) => {
                    const pos = positions[repo.id] || { x: 50, y: 50 };
                    return (
                        <div
                            key={repo.id}
                            className={`repo-block ${selected === repo.id ? 'selected' : ''}`}
                            style={{ left: pos.x, top: pos.y }}
                            onMouseDown={(e) => handleMouseDown(e, repo.id)}
                        >
                            <div className="repo-block-name">{repo.repo_name}</div>
                            <div className="repo-block-status flex items-center gap-8">
                                <span style={{
                                    width: 8, height: 8, borderRadius: '50%',
                                    background: statusColors[repo.status] || 'var(--text-muted)',
                                    display: 'inline-block',
                                }} />
                                <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>{repo.status}</span>
                            </div>
                            {!connecting && (
                                <button
                                    className="btn btn-secondary btn-sm mt-8"
                                    onClick={(e) => { e.stopPropagation(); startConnecting(repo.id); }}
                                    style={{ fontSize: 11, padding: '4px 10px' }}
                                >
                                    🔗 Connect
                                </button>
                            )}
                        </div>
                    );
                })}

                {repos.length === 0 && (
                    <div className="empty-state" style={{ minHeight: 400 }}>
                        <div className="empty-state-icon">🎨</div>
                        <p className="empty-state-text">Add repositories to see them on the canvas</p>
                    </div>
                )}
            </div>
        </div>
    );
}


// ─── Diff Viewer Component ──────────────────────────────────────────────────
function DiffViewer({ diffFiles }) {
    if (!diffFiles || diffFiles.length === 0) {
        return <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>No file changes in this commit.</p>;
    }

    return (
        <div className="flex-col gap-16">
            {diffFiles.map((file, idx) => (
                <div key={idx} className="diff-container">
                    <div className="diff-file-header">
                        <span style={{ marginRight: 12 }}>
                            {file.status === 'added' && <span className="badge badge-success" style={{ marginRight: 8 }}>A</span>}
                            {file.status === 'modified' && <span className="badge badge-warning" style={{ marginRight: 8 }}>M</span>}
                            {file.status === 'removed' && <span className="badge badge-danger" style={{ marginRight: 8 }}>D</span>}
                        </span>
                        {file.filename}
                    </div>
                    {file.patch ? (
                        <div>
                            {file.patch.split('\n').map((line, i) => {
                                let cls = 'diff-line context';
                                if (line.startsWith('+')) cls = 'diff-line added';
                                else if (line.startsWith('-')) cls = 'diff-line removed';
                                return <div key={i} className={cls}>{line}</div>;
                            })}
                        </div>
                    ) : (
                        <div style={{ padding: '16px', color: 'var(--text-muted)', fontSize: 13 }}>
                            No patch data available
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
}


// ─── Impact Panel Component ────────────────────────────────────────────────
function ImpactPanel({ reports }) {
    if (!reports || reports.length === 0) {
        return (
            <div className="impact-panel">
                <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>No impact analysis available for this commit.</p>
            </div>
        );
    }

    const levelBadge = {
        high: 'badge-danger',
        medium: 'badge-warning',
        low: 'badge-success',
        none: 'badge-muted',
        error: 'badge-danger',
    };

    return (
        <div className="impact-panel">
            <div className="impact-header">
                <h3 className="card-title">🎯 Impact Analysis</h3>
            </div>

            {reports.map((report) => (
                <div key={report.id} style={{ marginBottom: 24 }}>
                    <div className="flex items-center gap-12 mb-16">
                        <span className={`badge ${levelBadge[report.impact_level] || 'badge-muted'}`}>
                            {report.impact_level}
                        </span>
                        <span style={{ fontSize: 13, fontFamily: "'Courier New', monospace", color: 'var(--accent)' }}>
                            {report.changed_file}
                        </span>
                        <span className="badge badge-muted">{report.blast_zone_size} affected</span>
                    </div>

                    <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 16, lineHeight: 1.6 }}>
                        {report.summary}
                    </p>

                    {/* Affected Items */}
                    {report.affected_items && report.affected_items.length > 0 && (
                        <div className="mb-16">
                            <h4 style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 10 }}>
                                Affected Symbols
                            </h4>
                            {report.affected_items.map((item, i) => (
                                <div key={i} className="impact-item">
                                    <div className="impact-file">{item.file}</div>
                                    <div className="impact-symbol">
                                        {item.symbol_type === 'function' ? '⚡' : '📦'} {item.symbol}
                                        {item.line_number && <span style={{ color: 'var(--text-muted)' }}> (line {item.line_number})</span>}
                                        {item.breaking && <span className="badge badge-danger" style={{ marginLeft: 8 }}>BREAKING</span>}
                                    </div>
                                    {item.impact_reason && (
                                        <div className="impact-reason">{item.impact_reason}</div>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Recommendations */}
                    {report.recommendations && report.recommendations.length > 0 && (
                        <div>
                            <h4 style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 10 }}>
                                💡 Recommendations
                            </h4>
                            <ul style={{ listStyle: 'none', padding: 0 }}>
                                {report.recommendations.map((rec, i) => (
                                    <li key={i} style={{
                                        fontSize: 13, color: 'var(--text-secondary)',
                                        padding: '8px 12px', background: 'var(--bg-card)',
                                        borderRadius: 'var(--radius-sm)', marginBottom: 6,
                                        borderLeft: '3px solid var(--accent)',
                                    }}>
                                        {rec}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
}


// ─── Main Page ────────────────────────────────────────────────────────────────
export default function ProjectDetail() {
    const { id } = useParams();
    const router = useRouter();
    const [project, setProject] = useState(null);
    const [loading, setLoading] = useState(true);
    const [tab, setTab] = useState('repos');

    // Repos tab
    const [repoUrl, setRepoUrl] = useState('');
    const [adding, setAdding] = useState(false);
    const [processing, setProcessing] = useState(false);

    // Commits tab
    const [commits, setCommits] = useState([]);
    const [selectedCommit, setSelectedCommit] = useState(null);
    const [commitDetail, setCommitDetail] = useState(null);
    const [impactReports, setImpactReports] = useState([]);

    // Polling for processing status
    const [polling, setPolling] = useState(false);

    useEffect(() => {
        loadProject();
    }, [id]);

    useEffect(() => {
        if (tab === 'commits') loadCommits();
    }, [tab]);

    async function loadProject() {
        try {
            const data = await api.getProject(id);
            setProject(data);
        } catch {
            router.push('/');
        } finally {
            setLoading(false);
        }
    }

    async function loadCommits() {
        try {
            const data = await api.listCommits(id);
            setCommits(data);
        } catch { /* ignore */ }
    }

    async function handleAddRepo(e) {
        e.preventDefault();
        if (!repoUrl.trim()) return;
        setAdding(true);
        try {
            await api.addRepo(id, repoUrl.trim());
            setRepoUrl('');
            loadProject();
        } catch (err) {
            alert(err.message);
        } finally {
            setAdding(false);
        }
    }

    async function handleDeleteRepo(repoId) {
        if (!confirm('Remove this repository?')) return;
        try {
            await api.deleteRepo(id, repoId);
            loadProject();
        } catch (err) {
            alert(err.message);
        }
    }

    async function handleProcessAll() {
        setProcessing(true);
        try {
            await api.processAll(id);
            // Start polling for status updates
            setPolling(true);
            const interval = setInterval(async () => {
                const data = await api.getProject(id);
                setProject(data);
                const allDone = data.repositories.every(r => r.status === 'ready' || r.status === 'error');
                if (allDone) {
                    clearInterval(interval);
                    setPolling(false);
                    setProcessing(false);
                }
            }, 3000);
        } catch (err) {
            alert(err.message);
            setProcessing(false);
        }
    }

    async function handleSelectCommit(commit) {
        setSelectedCommit(commit);
        try {
            const detail = await api.getCommit(id, commit.id);
            setCommitDetail(detail);
            const impact = await api.getCommitImpact(id, commit.id);
            setImpactReports(impact);
        } catch { /* ignore */ }
    }

    async function handleDeleteProject() {
        if (!confirm('Delete this project and all its data? This cannot be undone.')) return;
        try {
            await api.deleteProject(id);
            router.push('/');
        } catch (err) {
            alert(err.message);
        }
    }

    async function handleSyncCommits() {
        setProcessing(true);
        try {
            const res = await api.syncCommits(id);
            alert(`Synced ${res.new_commits} new commits!`);
            loadCommits();
        } catch (err) {
            alert(err.message);
        } finally {
            setProcessing(false);
        }
    }

    if (loading) {
        return (
            <div className="app-shell">
                <Sidebar />
                <main className="main-content">
                    <div className="empty-state">
                        <div className="spinner" style={{ width: 32, height: 32 }}></div>
                    </div>
                </main>
            </div>
        );
    }

    if (!project) return null;

    const pendingCount = project.repositories.filter(r => r.status === 'pending' || r.status === 'error').length;

    return (
        <div className="app-shell">
            <Sidebar />
            <main className="main-content animate-in">
                {/* Header */}
                <div className="page-header">
                    <div className="flex items-center justify-between">
                        <div>
                            <div className="flex items-center gap-12">
                                <button className="btn btn-secondary btn-sm btn-icon" onClick={() => router.push('/')}>
                                    ←
                                </button>
                                <h1 className="page-title">{project.name}</h1>
                            </div>
                            <p className="page-subtitle">{project.description || 'No description'}</p>
                        </div>
                        <button className="btn btn-danger btn-sm" onClick={handleDeleteProject}>
                            🗑️ Delete
                        </button>
                    </div>
                </div>

                {/* Stat Bar */}
                <div className="stat-bar">
                    <div className="stat-card">
                        <div className="stat-icon blue">🔗</div>
                        <div>
                            <div className="stat-value">{project.repositories.length}</div>
                            <div className="stat-label">Repositories</div>
                        </div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-icon green">✅</div>
                        <div>
                            <div className="stat-value">
                                {project.repositories.filter(r => r.status === 'ready').length}
                            </div>
                            <div className="stat-label">Processed</div>
                        </div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-icon purple">🔀</div>
                        <div>
                            <div className="stat-value">{project.connections.length}</div>
                            <div className="stat-label">Connections</div>
                        </div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-icon orange">📝</div>
                        <div>
                            <div className="stat-value">{commits.length}</div>
                            <div className="stat-label">Commits</div>
                        </div>
                    </div>
                </div>

                {/* Tabs */}
                <div className="tabs">
                    {['repos', 'canvas', 'commits', 'impact'].map((t) => (
                        <button
                            key={t}
                            className={`tab ${tab === t ? 'active' : ''}`}
                            onClick={() => setTab(t)}
                        >
                            {t === 'repos' && '📦 Repositories'}
                            {t === 'canvas' && '🎨 Canvas'}
                            {t === 'commits' && '📝 Commits'}
                            {t === 'impact' && '🎯 Impact'}
                        </button>
                    ))}
                </div>

                {/* ─── Repositories Tab ───────────────────────────────────────────── */}
                {tab === 'repos' && (
                    <div>
                        <form onSubmit={handleAddRepo} className="input-group mb-24">
                            <input
                                className="input"
                                placeholder="https://github.com/user/repo.git"
                                value={repoUrl}
                                onChange={(e) => setRepoUrl(e.target.value)}
                            />
                            <button type="submit" className="btn btn-secondary" disabled={!repoUrl.trim() || adding}>
                                {adding ? <div className="spinner"></div> : '+ Add Repo'}
                            </button>
                            <button
                                type="button"
                                className="btn btn-primary"
                                onClick={handleProcessAll}
                                disabled={processing || pendingCount === 0}
                            >
                                {processing ? (
                                    <><div className="spinner"></div> Processing...</>
                                ) : (
                                    `⚡ Process All ${pendingCount > 0 ? `(${pendingCount})` : ''}`
                                )}
                            </button>
                        </form>

                        {project.repositories.length === 0 ? (
                            <div className="empty-state">
                                <div className="empty-state-icon">🔗</div>
                                <p className="empty-state-text">
                                    Add GitHub repository URLs above, then click &quot;Process All&quot; to build the knowledge graph.
                                </p>
                            </div>
                        ) : (
                            <div className="flex-col gap-12">
                                {project.repositories.map((repo) => (
                                    <div key={repo.id} className="card flex items-center justify-between" style={{ padding: '16px 20px' }}>
                                        <div className="flex items-center gap-16">
                                            <div>
                                                <div style={{ fontWeight: 600, fontSize: 15 }}>{repo.repo_name}</div>
                                                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{repo.repo_url}</div>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-12">
                                            <span className={`badge ${repo.status === 'ready' ? 'badge-success' :
                                                repo.status === 'processing' ? 'badge-warning' :
                                                    repo.status === 'error' ? 'badge-danger' : 'badge-muted'
                                                }`}>
                                                {repo.status}
                                            </span>
                                            {repo.files_processed > 0 && (
                                                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                                                    {repo.files_processed} files
                                                </span>
                                            )}
                                            <button className="btn btn-danger btn-sm btn-icon" onClick={() => handleDeleteRepo(repo.id)}>
                                                ✕
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}

                        {processing && (
                            <div className="progress-bar mt-16">
                                <div className="progress-fill" style={{ width: '60%', animation: 'pulse 1.5s infinite' }} />
                            </div>
                        )}
                    </div>
                )}

                {/* ─── Canvas Tab ─────────────────────────────────────────────────── */}
                {tab === 'canvas' && (
                    <RepoCanvas
                        repos={project.repositories}
                        connections={project.connections}
                        projectId={id}
                        onConnectionCreated={loadProject}
                    />
                )}

                {/* ─── Commits Tab ────────────────────────────────────────────────── */}
                {tab === 'commits' && (
                    <div>
                        <div className="flex justify-end mb-16">
                            <button
                                className="btn btn-primary btn-sm"
                                onClick={handleSyncCommits}
                                disabled={processing}
                            >
                                {processing ? 'Syncing...' : '🔄 Sync Commits'}
                            </button>
                        </div>
                        {commits.length === 0 ? (
                            <div className="empty-state">
                                <div className="empty-state-icon">📝</div>
                                <p className="empty-state-text">
                                    No commits received yet. Set up a GitHub webhook pointing to your server&apos;s <code>/api/v1/webhook/github</code> endpoint.
                                </p>
                            </div>
                        ) : (
                            <div>
                                {selectedCommit ? (
                                    <div>
                                        <button className="btn btn-secondary btn-sm mb-24" onClick={() => { setSelectedCommit(null); setCommitDetail(null); }}>
                                            ← Back to Commits
                                        </button>
                                        <div className="split-view">
                                            <div>
                                                <h3 className="card-title mb-16">
                                                    <span className="commit-sha">{selectedCommit.sha?.slice(0, 7)}</span>
                                                    {' '}{selectedCommit.message}
                                                </h3>
                                                <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 20 }}>
                                                    by {selectedCommit.author} on {selectedCommit.repo_name} · {selectedCommit.branch}
                                                </div>
                                                {commitDetail && <DiffViewer diffFiles={commitDetail.diff_files} />}
                                            </div>
                                            <ImpactPanel reports={impactReports} />
                                        </div>
                                    </div>
                                ) : (
                                    <div className="flex-col gap-8">
                                        {commits.map((c) => (
                                            <div key={c.id} className="commit-item" onClick={() => handleSelectCommit(c)}>
                                                <div className="commit-sha">{c.sha?.slice(0, 7)}</div>
                                                <div style={{ flex: 1 }}>
                                                    <div className="commit-message">{c.message}</div>
                                                    <div className="commit-meta mt-8">
                                                        <span>👤 {c.author}</span>
                                                        <span>📦 {c.repo_name}</span>
                                                        <span>🌿 {c.branch}</span>
                                                        <span>{c.files_changed} files</span>
                                                    </div>
                                                </div>
                                                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                                                    {c.received_at ? new Date(c.received_at).toLocaleString() : ''}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                )}

                {/* ─── Impact Tab (latest) ────────────────────────────────────────── */}
                {tab === 'impact' && (
                    <div>
                        {commits.length === 0 ? (
                            <div className="empty-state">
                                <div className="empty-state-icon">🎯</div>
                                <p className="empty-state-text">Impact analysis will appear here when commits are received via webhook.</p>
                            </div>
                        ) : (
                            <div>
                                <p style={{ fontSize: 14, color: 'var(--text-muted)', marginBottom: 20 }}>
                                    Select a commit from the Commits tab to view its impact analysis, or see the latest below.
                                </p>
                                {commits.slice(0, 5).map((c) => (
                                    <div key={c.id} className="card mb-16" style={{ cursor: 'pointer' }} onClick={() => { setTab('commits'); handleSelectCommit(c); }}>
                                        <div className="flex items-center gap-12">
                                            <span className="commit-sha">{c.sha?.slice(0, 7)}</span>
                                            <span style={{ fontSize: 14 }}>{c.message}</span>
                                            <span className="badge badge-muted">{c.files_changed} files</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}
            </main>
        </div>
    );
}
