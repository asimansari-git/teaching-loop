import { useState, useEffect } from 'react'
import { useAuth } from '@/context/auth-context'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ShieldAlert, Loader2, LogOut } from 'lucide-react'

export function SessionExpiredModal() {
  const { user, login, logout } = useAuth()
  const [isOpen, setIsOpen] = useState(false)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (user?.username) {
      setUsername(user.username)
    }
  }, [user])

  useEffect(() => {
    const handleUnauthorized = (e: Event) => {
      const customEvent = e as CustomEvent<{ message?: string }>
      setError(customEvent.detail?.message || 'Your session has timed out. Please authenticate to continue.')
      setIsOpen(true)
    }

    window.addEventListener('socratic:unauthorized', handleUnauthorized)
    return () => {
      window.removeEventListener('socratic:unauthorized', handleUnauthorized)
    }
  }, [])

  const handleReLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!username.trim() || !password) {
      setError('Please provide both username and password.')
      return
    }

    setLoading(true)
    setError(null)
    try {
      await login(username.trim(), password)
      setIsOpen(false)
      setPassword('')
    } catch (err: any) {
      setError(err.message || 'Failed to re-authenticate. Please verify credentials.')
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = () => {
    setIsOpen(false)
    logout()
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !loading && setIsOpen(open)}>
      <DialogContent className="max-w-md p-6 bg-card text-card-foreground border-border shadow-lg">
        <DialogHeader className="space-y-2">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-full bg-amber-500/10 text-amber-500">
              <ShieldAlert className="h-5 w-5" />
            </div>
            <DialogTitle className="text-lg font-bold text-foreground">Session Timed Out</DialogTitle>
          </div>
          <DialogDescription className="text-xs text-muted-foreground">
            Your login session has expired. Re-enter your credentials to resume learning without losing your workspace state.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleReLogin} className="space-y-4 my-2">
          {error && (
            <div className="p-2.5 rounded-md text-xs bg-destructive/15 text-destructive font-medium border border-destructive/20">
              {error}
            </div>
          )}

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-foreground">Username</label>
            <Input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Username"
              disabled={loading}
              className="h-9 text-xs"
              required
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-foreground">Password</label>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              disabled={loading}
              className="h-9 text-xs"
              autoFocus
              required
            />
          </div>

          <DialogFooter className="flex flex-col sm:flex-row gap-2 pt-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleLogout}
              disabled={loading}
              className="sm:w-auto text-xs"
            >
              <LogOut className="h-3.5 w-3.5 mr-1 text-muted-foreground" />
              Sign Out
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={loading}
              className="sm:w-auto text-xs font-medium"
            >
              {loading ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                  Verifying...
                </>
              ) : (
                'Re-authenticate'
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
