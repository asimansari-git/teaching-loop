import { BookOpen, LogOut, User as UserIcon, GraduationCap, School } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ThemeToggle } from '@/components/theme-toggle'
import { useAuth } from '@/context/auth-context'

interface NavbarProps {
  activeView?: 'workspace' | 'teacher-dashboard'
  onViewChange?: (view: 'workspace' | 'teacher-dashboard') => void
}

export function Navbar({ activeView, onViewChange }: NavbarProps) {
  const { user, logout } = useAuth()

  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-14 items-center justify-between px-4">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 font-bold text-lg text-primary">
            <BookOpen className="h-5 w-5 text-primary" />
            <span>Teach Loop</span>
          </div>

          {user && (
            <Badge
              variant={user.role === 'teacher' ? 'default' : 'secondary'}
              className="hidden sm:flex items-center gap-1 ml-2 capitalize"
            >
              {user.role === 'teacher' ? (
                <School className="h-3 w-3" />
              ) : (
                <GraduationCap className="h-3 w-3" />
              )}
              {user.role}
            </Badge>
          )}
        </div>

        {user && onViewChange && user.role === 'teacher' && (
          <div className="flex items-center gap-1 bg-muted p-1 rounded-lg">
            <Button
              variant={activeView === 'workspace' ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => onViewChange('workspace')}
              className="text-xs"
            >
              Dual-Pane Workspace
            </Button>
            <Button
              variant={activeView === 'teacher-dashboard' ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => onViewChange('teacher-dashboard')}
              className="text-xs"
            >
              Teacher Overview
            </Button>
          </div>
        )}

        <div className="flex items-center gap-2">
          {user ? (
            <div className="flex items-center gap-2">
              <div className="hidden md:flex items-center gap-1.5 text-xs text-muted-foreground bg-muted px-2.5 py-1 rounded-full">
                <UserIcon className="h-3.5 w-3.5" />
                <span className="font-medium text-foreground">{user.username}</span>
              </div>
              <ThemeToggle />
              <Button variant="ghost" size="icon" onClick={logout} title="Log out">
                <LogOut className="h-4 w-4" />
                <span className="sr-only">Log out</span>
              </Button>
            </div>
          ) : (
            <ThemeToggle />
          )}
        </div>
      </div>
    </header>
  )
}
