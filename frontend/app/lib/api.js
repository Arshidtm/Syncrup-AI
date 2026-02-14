const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function apiFetch(path, options = {}) {
    const res = await fetch(`${API}${path}`, {
        headers: { 'Content-Type': 'application/json', ...options.headers },
        ...options,
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'API error');
    }
    return res.json();
}

export const api = {
    // Projects
    listProjects: () => apiFetch('/api/v1/projects'),
    createProject: (data) => apiFetch('/api/v1/projects', { method: 'POST', body: JSON.stringify(data) }),
    getProject: (id) => apiFetch(`/api/v1/projects/${id}`),
    deleteProject: (id) => apiFetch(`/api/v1/projects/${id}`, { method: 'DELETE' }),

    // Repositories
    addRepo: (pid, repo_url) => apiFetch(`/api/v1/projects/${pid}/repositories`, { method: 'POST', body: JSON.stringify({ repo_url }) }),
    deleteRepo: (pid, rid) => apiFetch(`/api/v1/projects/${pid}/repositories/${rid}`, { method: 'DELETE' }),
    processAll: (pid) => apiFetch(`/api/v1/projects/${pid}/repositories/process-all`, { method: 'POST' }),

    // Connections
    createConnection: (pid, data) => apiFetch(`/api/v1/projects/${pid}/connections`, { method: 'POST', body: JSON.stringify(data) }),
    listConnections: (pid) => apiFetch(`/api/v1/projects/${pid}/connections`),
    deleteConnection: (pid, cid) => apiFetch(`/api/v1/projects/${pid}/connections/${cid}`, { method: 'DELETE' }),

    // Graph
    getGraph: (pid) => apiFetch(`/api/v1/projects/${pid}/graph`).catch(() => ({ nodes: [], edges: [] })),

    // Commits
    listCommits: (pid) => apiFetch(`/api/v1/projects/${pid}/commits`),
    getCommit: (pid, cid) => apiFetch(`/api/v1/projects/${pid}/commits/${cid}`),
    getCommitImpact: (pid, cid) => apiFetch(`/api/v1/projects/${pid}/commits/${cid}/impact`).catch(() => []),
    syncCommits: (pid) => apiFetch(`/api/v1/projects/${pid}/commits/sync`, { method: 'POST' }),
};
