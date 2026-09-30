import { useState, useEffect, useCallback } from 'react'
import { api, type SessionSummary, type ChatMessage, type TextbookArticle, type ReviewSheet } from '@/api/client'
import { SocraticReader } from '@/components/socratic-reader'
import { CompanionTutorDrawer } from '@/components/companion-tutor-drawer'
import { QuizModal } from '@/components/quiz-modal'
import { CertificateModal } from '@/components/certificate-modal'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { PanelRightClose, PanelRightOpen, Plus, Bot, BookOpen } from 'lucide-react'

export function Workspace() {
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string>('')
  const [sessionSubject, setSessionSubject] = useState<string>('General Socratic Session')

  // Content & Reader State
  const [article, setArticle] = useState<TextbookArticle | null>(null)
  const [articleLoading, setArticleLoading] = useState<boolean>(false)

  // Chat State
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [sendingMsg, setSendingMsg] = useState<boolean>(false)

  // Highlights & Review Sheet State
  const [highlights, setHighlights] = useState<Array<{ text: string; note?: string; section?: string }>>([])
  const [reviewSheet, setReviewSheet] = useState<ReviewSheet | null>(null)
  const [compilingSheet, setCompilingSheet] = useState<boolean>(false)

  // Drawer & Responsive Viewport Toggles
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(true)
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState<boolean>(false)

  // Modals
  const [isQuizOpen, setIsQuizOpen] = useState<boolean>(false)
  const [isCertOpen, setIsCertOpen] = useState<boolean>(false)
  const [isNewSessionOpen, setIsNewSessionOpen] = useState<boolean>(false)
  const [newSubject, setNewSubject] = useState<string>('')
  const [newTopics, setNewTopics] = useState<string>('')

  // Load Sessions list
  const loadSessions = useCallback(async () => {
    try {
      const data = await api.getSessions()
      setSessions(data)
      if (data.length > 0 && !activeSessionId) {
        setActiveSessionId(data[0].id)
        setSessionSubject(data[0].subject)
      }
    } catch (err) {
      console.error('Failed to load sessions:', err)
    }
  }, [activeSessionId])

  useEffect(() => {
    loadSessions()
  }, [loadSessions])

  // Load Active Session details & history
  const loadSessionDetails = useCallback(async (sessionId: string) => {
    if (!sessionId) return
    try {
      const history = await api.getHistory(sessionId)
      setMessages(history.messages || [])
      setSessionSubject(history.subject || 'Socratic Session')

      // Attempt to load generated textbook article
      setArticleLoading(true)
      const tb = await api.generateTextbook(sessionId)
      setArticle(tb)
    } catch (err) {
      console.error('Error fetching session details:', err)
    } finally {
      setArticleLoading(false)
    }
  }, [])

  useEffect(() => {
    if (activeSessionId) {
      loadSessionDetails(activeSessionId)
    }
  }, [activeSessionId, loadSessionDetails])

  // Handlers
  const handleStartNewSession = async () => {
    if (!newSubject.trim()) return
    try {
      const topicsArr = newTopics.split(',').map((t) => t.trim()).filter(Boolean)
      const res = await api.startSession(newSubject.trim(), topicsArr)
      setIsNewSessionOpen(false)
      setNewSubject('')
      setNewTopics('')
      await loadSessions()
      setActiveSessionId(res.session_id)
    } catch (err) {
      console.error('Failed to start new session:', err)
    }
  }

  const handleGenerateArticle = async () => {
    if (!activeSessionId) return
    setArticleLoading(true)
    try {
      const data = await api.generateTextbook(activeSessionId)
      setArticle(data)
    } catch (err) {
      console.error('Failed to generate article:', err)
    } finally {
      setArticleLoading(false)
    }
  }

  const handleSendMessage = async (promptMsg: string) => {
    if (!activeSessionId) return
    setSendingMsg(true)
    const newMsg: ChatMessage = { role: 'user', content: promptMsg }
    setMessages((prev) => [...prev, newMsg])

    try {
      const res = await api.sendMessage(activeSessionId, promptMsg)
      const botMsg: ChatMessage = { role: 'assistant', content: res.response }
      setMessages((prev) => [...prev, botMsg])
    } catch (err) {
      console.error('Failed to send message:', err)
    } finally {
      setSendingMsg(false)
    }
  }

  const handleAskAboutSelection = (selectedText: string) => {
    const prompt = `Can you explain or elaborate on this excerpt from the text: "${selectedText}"?`
    if (window.innerWidth < 768) {
      setMobileDrawerOpen(true)
    } else {
      setIsDrawerOpen(true)
    }
    handleSendMessage(prompt)
  }

  const handleGetSocraticHint = async (question: string) => {
    if (!activeSessionId) return
    setSendingMsg(true)
    try {
      const hintRes = await api.getSocraticHint(activeSessionId, question, article?.markdown_content)
      const hintText = hintRes.excerpt
        ? `**Socratic Hint**: ${hintRes.hint}\n\n*Relevant Excerpt*: "${hintRes.excerpt}"`
        : `**Socratic Hint**: ${hintRes.hint}`
      const botMsg: ChatMessage = { role: 'assistant', content: hintText }
      setMessages((prev) => [...prev, botMsg])
    } catch (err) {
      console.error('Failed to get socratic hint:', err)
    } finally {
      setSendingMsg(false)
    }
  }

  const handleAddHighlight = (highlight: { text: string; note?: string; section?: string }) => {
    setHighlights((prev) => [...prev, highlight])
  }

  const handleRemoveHighlight = (index: number) => {
    setHighlights((prev) => prev.filter((_, i) => i !== index))
  }

  const handleCompileReviewSheet = async () => {
    if (!activeSessionId || highlights.length === 0) return
    setCompilingSheet(true)
    try {
      const sheet = await api.compileReviewSheet(activeSessionId, highlights)
      setReviewSheet(sheet)
    } catch (err) {
      console.error('Failed to compile review sheet:', err)
    } finally {
      setCompilingSheet(false)
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)] bg-background">
      {/* Session Navigation Bar */}
      <div className="flex items-center justify-between px-4 py-2 border-b bg-muted/20 text-xs gap-3">
        <div className="flex items-center gap-2 overflow-x-auto">
          <Select value={activeSessionId} onValueChange={setActiveSessionId}>
            <SelectTrigger className="w-[220px] h-8 text-xs bg-background">
              <SelectValue placeholder="Select active session" />
            </SelectTrigger>
            <SelectContent>
              {sessions.map((s) => (
                <SelectItem key={s.id} value={s.id}>
                  {s.subject}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Button size="sm" variant="outline" className="h-8 text-xs" onClick={() => setIsNewSessionOpen(true)}>
            <Plus className="h-3.5 w-3.5 mr-1" /> New Session
          </Button>
        </div>

        {/* Drawer Desktop Toggle & Mobile Sheet Trigger */}
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            className="hidden md:flex items-center gap-1.5 h-8 text-xs"
            onClick={() => setIsDrawerOpen(!isDrawerOpen)}
          >
            {isDrawerOpen ? (
              <>
                <PanelRightClose className="h-4 w-4" /> Collapse Tutor
              </>
            ) : (
              <>
                <PanelRightOpen className="h-4 w-4 text-primary" /> Expand Tutor
              </>
            )}
          </Button>

          {/* Mobile Viewport Sheet Trigger */}
          <div className="md:hidden">
            <Sheet open={mobileDrawerOpen} onOpenChange={setMobileDrawerOpen}>
              <SheetTrigger asChild>
                <Button size="sm" className="h-8 text-xs">
                  <Bot className="h-3.5 w-3.5 mr-1" /> Companion Tutor
                </Button>
              </SheetTrigger>
              <SheetContent side="right" className="w-full sm:max-w-md p-0">
                <SheetHeader className="p-4 pb-0">
                  <SheetTitle className="text-sm font-bold flex items-center gap-2">
                    <BookOpen className="h-4 w-4 text-primary" /> Mobile Socratic Tutor
                  </SheetTitle>
                </SheetHeader>
                <div className="h-[calc(100vh-4rem)]">
                  <CompanionTutorDrawer
                    messages={messages}
                    sending={sendingMsg}
                    onSendMessage={handleSendMessage}
                    onGetSocraticHint={handleGetSocraticHint}
                    highlights={highlights}
                    onRemoveHighlight={handleRemoveHighlight}
                    onCompileReviewSheet={handleCompileReviewSheet}
                    reviewSheet={reviewSheet}
                    compilingSheet={compilingSheet}
                  />
                </div>
              </SheetContent>
            </Sheet>
          </div>
        </div>
      </div>

      {/* Dual-Pane Workspace Core Stage */}
      <div className="flex-1 flex overflow-hidden">
        {/* Primary Stage: Socratic Reader */}
        <SocraticReader
          article={article}
          loading={articleLoading}
          sessionSubject={sessionSubject}
          onGenerateArticle={handleGenerateArticle}
          onAskAboutSelection={handleAskAboutSelection}
          onAddHighlight={handleAddHighlight}
          onOpenQuizModal={() => setIsQuizOpen(true)}
          onGenerateCertificate={() => setIsCertOpen(true)}
        />

        {/* Desktop Collapsible Companion Tutor Drawer */}
        {isDrawerOpen && (
          <div className="hidden md:block w-[380px] lg:w-[440px] shrink-0 h-full transition-all duration-300">
            <CompanionTutorDrawer
              messages={messages}
              sending={sendingMsg}
              onSendMessage={handleSendMessage}
              onGetSocraticHint={handleGetSocraticHint}
              highlights={highlights}
              onRemoveHighlight={handleRemoveHighlight}
              onCompileReviewSheet={handleCompileReviewSheet}
              reviewSheet={reviewSheet}
              compilingSheet={compilingSheet}
            />
          </div>
        )}
      </div>

      {/* Modals */}
      <QuizModal
        isOpen={isQuizOpen}
        onClose={() => setIsQuizOpen(false)}
        sessionId={activeSessionId}
      />

      <CertificateModal
        isOpen={isCertOpen}
        onClose={() => setIsCertOpen(false)}
        sessionId={activeSessionId}
        subject={sessionSubject}
      />

      {/* New Session Creation Dialog */}
      <Dialog open={isNewSessionOpen} onOpenChange={setIsNewSessionOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Start New Socratic Learning Session</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <label className="text-xs font-medium">Subject / Course Name</label>
              <Input
                placeholder="e.g. Physics, Data Structures, Ethics"
                value={newSubject}
                onChange={(e) => setNewSubject(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium">Topics (comma separated)</label>
              <Input
                placeholder="e.g. Newton's Laws, Momentum, Friction"
                value={newTopics}
                onChange={(e) => setNewTopics(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsNewSessionOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleStartNewSession} disabled={!newSubject.trim()}>
              Start Session
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
