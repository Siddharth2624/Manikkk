import { Navbar } from './navbar';

export function Layout({ currentRole, children }) {
  return (
    <div className="min-h-screen bg-background">
      <Navbar currentRole={currentRole} />
      <main className="container mx-auto py-6 px-4">
        {children}
      </main>
    </div>
  );
}
