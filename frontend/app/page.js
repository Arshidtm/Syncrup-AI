'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Sidebar from './components/Sidebar';
import { api } from './lib/api';

export default function Dashboard() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [name, setName] = useState('');
  const [desc, setDesc] = useState('');
  const [creating, setCreating] = useState(false);
  const router = useRouter();

  useEffect(() => {
    loadProjects();
  }, []);

  async function loadProjects() {
    try {
      const data = await api.listProjects();
      setProjects(data);
    } catch {
      // Ignore — backend may be down
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(e) {
    e.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    try {
      const project = await api.createProject({ name: name.trim(), description: desc.trim() });
      setShowModal(false);
      setName('');
      setDesc('');
      router.push(`/projects/${project.id}`);
    } catch (err) {
      alert(err.message);
    } finally {
      setCreating(false);
    }
  }

  const totalRepos = projects.reduce((acc, p) => acc + (p.repo_count || 0), 0);

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content animate-in">
        <div className="page-header flex justify-between items-center">
          <div>
            <h1 className="page-title">Dashboard</h1>
            <p className="page-subtitle">Manage your projects and repositories</p>
          </div>
          <button className="btn btn-primary" onClick={() => setShowModal(true)}>
            ✦ New Project
          </button>
        </div>

        {/* Stats */}
        <div className="stat-bar">
          <div className="stat-card">
            <div className="stat-icon blue">📁</div>
            <div>
              <div className="stat-value">{projects.length}</div>
              <div className="stat-label">Projects</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon purple">🔗</div>
            <div>
              <div className="stat-value">{totalRepos}</div>
              <div className="stat-label">Repositories</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon green">✅</div>
            <div>
              <div className="stat-value">{projects.filter(p => p.repo_count > 0).length}</div>
              <div className="stat-label">Active Projects</div>
            </div>
          </div>
        </div>

        {/* Project Grid */}
        {loading ? (
          <div className="empty-state">
            <div className="spinner" style={{ width: 32, height: 32 }}></div>
            <p className="empty-state-text mt-16">Loading projects...</p>
          </div>
        ) : projects.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">📁</div>
            <p className="empty-state-text">
              No projects yet. Create your first project to start analyzing code dependencies.
            </p>
            <button className="btn btn-primary mt-24" onClick={() => setShowModal(true)}>
              ✦ Create First Project
            </button>
          </div>
        ) : (
          <div className="grid grid-2">
            {projects.map((project) => (
              <div
                key={project.id}
                className="card"
                onClick={() => router.push(`/projects/${project.id}`)}
                style={{ cursor: 'pointer' }}
              >
                <div className="card-header">
                  <h3 className="card-title">{project.name}</h3>
                  <span className="badge badge-info">{project.repo_count || 0} repos</span>
                </div>
                <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 12 }}>
                  {project.description || 'No description'}
                </p>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  Created {new Date(project.created_at).toLocaleDateString()}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Create Project Modal */}
        {showModal && (
          <div className="modal-overlay" onClick={() => setShowModal(false)}>
            <div className="modal" onClick={(e) => e.stopPropagation()}>
              <h2 className="modal-title">Create New Project</h2>
              <form onSubmit={handleCreate}>
                <div className="flex-col gap-16">
                  <div>
                    <label style={{ fontSize: 13, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>
                      Project Name *
                    </label>
                    <input
                      className="input w-full"
                      placeholder="e.g. my-microservices"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      autoFocus
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: 13, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>
                      Description
                    </label>
                    <textarea
                      className="input w-full"
                      placeholder="Brief description of your project..."
                      value={desc}
                      onChange={(e) => setDesc(e.target.value)}
                      rows={3}
                    />
                  </div>
                </div>
                <div className="modal-actions">
                  <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                    Cancel
                  </button>
                  <button type="submit" className="btn btn-primary" disabled={!name.trim() || creating}>
                    {creating ? <><div className="spinner"></div> Creating...</> : '✦ Create Project'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
