import './globals.css';

export const metadata = {
  title: 'Nexus AI Engine',
  description: 'AI-powered code impact analysis across repositories',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
