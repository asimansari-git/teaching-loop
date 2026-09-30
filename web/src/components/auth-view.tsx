import { useState, useEffect } from 'react'
import { api, type Organization } from '@/api/client'
import { useAuth } from '@/context/auth-context'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { BookOpen, AlertCircle, Loader2 } from 'lucide-react'

export function AuthView() {
  const { login, register } = useAuth()
  const [activeTab, setActiveTab] = useState<'login' | 'register'>('login')
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  // Login form state
  const [loginUsername, setLoginUsername] = useState('')
  const [loginPassword, setLoginPassword] = useState('')

  // Register form state
  const [regUsername, setRegUsername] = useState('')
  const [regPassword, setRegPassword] = useState('')
  const [regRole, setRegRole] = useState<'student' | 'teacher'>('student')
  const [regOrgId, setRegOrgId] = useState<string>('new')
  const [newOrgName, setNewOrgName] = useState('')
  const [organizations, setOrganizations] = useState<Organization[]>([])

  useEffect(() => {
    api
      .getOrganizations()
      .then((orgs) => {
        setOrganizations(orgs)
        if (orgs.length > 0) {
          setRegOrgId(String(orgs[0].id))
        } else {
          setRegOrgId('new')
        }
      })
      .catch((err) => console.error('Failed to load organizations:', err))
  }, [])

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await login(loginUsername, loginPassword)
    } catch (err: any) {
      setError(err.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await register({
        username: regUsername,
        password: regPassword,
        role: regRole,
        organization_id: regOrgId && regOrgId !== 'new' ? Number(regOrgId) : undefined,
        new_organization_name: regOrgId === 'new' ? newOrgName : undefined,
      })
    } catch (err: any) {
      setError(err.message || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background to-muted p-4">
      <Card className="w-full max-w-md shadow-xl border-border/50">
        <CardHeader className="text-center space-y-2">
          <div className="mx-auto bg-primary/10 p-3 rounded-full w-fit">
            <BookOpen className="h-8 w-8 text-primary" />
          </div>
          <CardTitle className="text-2xl font-bold">Socratic Workspace</CardTitle>
          <CardDescription>
            Decoupled Vite + React 19 AI-powered learning environment
          </CardDescription>
        </CardHeader>

        <CardContent>
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'login' | 'register')}>
            <TabsList className="grid w-full grid-cols-2 mb-6">
              <TabsTrigger value="login">Login</TabsTrigger>
              <TabsTrigger value="register">Register</TabsTrigger>
            </TabsList>

            {error && (
              <div className="mb-4 p-3 rounded-md bg-destructive/15 text-destructive text-sm flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <TabsContent value="login">
              <form onSubmit={handleLogin} className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Username</label>
                  <Input
                    placeholder="Enter your username"
                    value={loginUsername}
                    onChange={(e) => setLoginUsername(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Password</label>
                  <Input
                    type="password"
                    placeholder="••••••••"
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                    required
                  />
                </div>
                <Button type="submit" className="w-full" disabled={loading}>
                  {loading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Logging in...
                    </>
                  ) : (
                    'Sign In'
                  )}
                </Button>
              </form>
            </TabsContent>

            <TabsContent value="register">
              <form onSubmit={handleRegister} className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Username</label>
                  <Input
                    placeholder="Choose a username"
                    value={regUsername}
                    onChange={(e) => setRegUsername(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Password</label>
                  <Input
                    type="password"
                    placeholder="••••••••"
                    value={regPassword}
                    onChange={(e) => setRegPassword(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Role</label>
                  <select
                    className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                    value={regRole}
                    onChange={(e) => {
                      const role = e.target.value as 'student' | 'teacher'
                      setRegRole(role)
                      if (role === 'teacher' && organizations.length === 0) {
                        setRegOrgId('new')
                      }
                    }}
                  >
                    <option value="student" className="bg-background text-foreground">Student</option>
                    <option value="teacher" className="bg-background text-foreground">Teacher</option>
                  </select>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Organization</label>
                  <select
                    className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                    value={regOrgId}
                    onChange={(e) => setRegOrgId(e.target.value)}
                  >
                    {organizations.map((org) => (
                      <option key={org.id} value={String(org.id)} className="bg-background text-foreground">
                        {org.name}
                      </option>
                    ))}
                    {regRole === 'teacher' && (
                      <option value="new" className="bg-background text-foreground">
                        + Create New Organization
                      </option>
                    )}
                  </select>
                </div>

                {regRole === 'teacher' && (regOrgId === 'new' || organizations.length === 0) && (
                  <div className="space-y-2">
                    <label className="text-sm font-medium">New Organization Name</label>
                    <Input
                      placeholder="e.g. Science Department"
                      value={newOrgName}
                      onChange={(e) => setNewOrgName(e.target.value)}
                      required
                    />
                  </div>
                )}

                <Button type="submit" className="w-full" disabled={loading}>
                  {loading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Registering...
                    </>
                  ) : (
                    'Create Account'
                  )}
                </Button>
              </form>
            </TabsContent>
          </Tabs>
        </CardContent>

        <CardFooter className="justify-center border-t py-4 text-xs text-muted-foreground">
          Socratic AI Tutor Workspace &copy; 2025
        </CardFooter>
      </Card>
    </div>
  )
}
