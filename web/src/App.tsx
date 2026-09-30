import { useState } from 'react'
import { AuthProvider, useAuth } from '@/context/auth-context'
import { ThemeProvider } from '@/components/theme-provider'
import { Navbar } from '@/components/navbar'
import { AuthView } from '@/components/auth-view'
import { Workspace } from '@/components/workspace'
import { TeacherDashboard } from '@/components/teacher-dashboard'
import { Loader2 } from 'lucide-react'

function MainContent() {
  const { isAuthenticated, isLoading, user } = useAuth()
  const [activeView, setActiveView] = useState<'workspace' | 'teacher-dashboard'>('workspace')

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <AuthView />
  }

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      <Navbar activeView={activeView} onViewChange={setActiveView} />
      <main className="flex-1">
        {user?.role === 'teacher' && activeView === 'teacher-dashboard' ? (
          <TeacherDashboard />
        ) : (
          <Workspace />
        )}
      </main>
    </div>
  )
}

export default function App() {
  return (
    <ThemeProvider defaultTheme="system" storageKey="socratic-ui-theme">
      <AuthProvider>
        <MainContent />
      </AuthProvider>
    </ThemeProvider>
  )
}
