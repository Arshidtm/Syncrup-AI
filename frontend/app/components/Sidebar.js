'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function Sidebar() {
    const pathname = usePathname();

    const links = [
        { href: '/', label: 'Dashboard', icon: '📊' },
        { href: '/projects', label: 'Projects', icon: '📁' },
    ];

    return (
        <aside className="sidebar">
            <div className="sidebar-logo">
                <div className="sidebar-logo-icon">N</div>
                <div className="sidebar-logo-text">
                    <span>Nexus</span> AI
                </div>
            </div>

            <nav className="sidebar-nav">
                {links.map((link) => (
                    <Link
                        key={link.href}
                        href={link.href}
                        className={`sidebar-link ${pathname === link.href ? 'active' : ''}`}
                    >
                        <span className="sidebar-link-icon">{link.icon}</span>
                        {link.label}
                    </Link>
                ))}
            </nav>

            <div style={{ borderTop: '1px solid var(--border)', paddingTop: 16, marginTop: 'auto' }}>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                    Nexus AI Engine v1.0
                </div>
            </div>
        </aside>
    );
}
