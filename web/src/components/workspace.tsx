import { useState, useEffect, useCallback } from 'react'
import {
  api,
  type SessionSummary,
  type ChatMessage,
  type TextbookArticle,
  type ReviewSheet,
  type LearningPlan,
} from '@/api/client'
import { SocraticReader } from '@/components/socratic-reader'
import { BigChatView } from '@/components/big-chat-view'
import { CompanionTutorDrawer } from '@/components/companion-tutor-drawer'
import { QuizModal } from '@/components/quiz-modal'
import { CertificateModal } from '@/components/certificate-modal'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import {
  PanelRightClose,
  PanelRightOpen,
  Plus,
  BookOpen,
  MessageSquare,
  Compass,
} from 'lucide-react'

export function Workspace() {
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string>('')
  const [sessionSubject, setSessionSubject] = useState<string>('General Socratic Session')

  // Primary Stage Mode: 'reader' | 'chat'
  const [stageMode, setStageMode] = useState<'reader' | 'chat'>('chat')

  // Content & Reader State
  const [article, setArticle] = useState<TextbookArticle | null>(null)
  const [articleLoading, setArticleLoading] = useState<boolean>(false)

  // Chat State
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [sendingMsg, setSendingMsg] = useState<boolean>(false)

  // Learning Plan State
  const [learningPlan, setLearningPlan] = useState<LearningPlan | null>(null)
  const [loadingPlan, setLoadingPlan] = useState<boolean>(false)

  // Highlights & Review Sheet State
  const [highlights, setHighlights] = useState<Array<{ text: string; note?: string; section?: string }>>([])
  const [reviewSheet, setReviewSheet] = useState<ReviewSheet | null>(null)
  const [compilingSheet, setCompilingSheet] = useState<boolean>(false)

  // Drawer & Responsive Viewport Toggles
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(true)
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState<boolean>(false)

  // Modals
  // Modals & New Session Dialog State
  const [isQuizOpen, setIsQuizOpen] = useState<boolean>(false)
  const [isCertOpen, setIsCertOpen] = useState<boolean>(false)
  const [isNewSessionOpen, setIsNewSessionOpen] = useState<boolean>(false)

  // Subject & Topic Discovery State
  const [subjectSource, setSubjectSource] = useState<'preset' | 'custom'>('preset')
  const [availableSubjects, setAvailableSubjects] = useState<Array<{ id: number; name: string; topics: string[] }>>([])
  const [selectedPresetSubject, setSelectedPresetSubject] = useState<string>('')
  const [customSubjectInput, setCustomSubjectInput] = useState<string>('')
  const [validatingSubject, setValidatingSubject] = useState<boolean>(false)
  const [discoveredTopics, setDiscoveredTopics] = useState<string[]>([])
  const [selectedTopics, setSelectedTopics] = useState<string[]>([])
  const [creatingSession, setCreatingSession] = useState<boolean>(false)

  // Load Sessions list
  const loadSessions = useCallback(async () => {
    try {
      const data = await api.getSessions()
      setSessions(data)
      if (data.length > 0 && !activeSessionId) {
        setActiveSessionId(data[0].id)
        setSessionSubject(data[0].title || data[0].subject)
      }
    } catch (err) {
      console.error('Failed to load sessions:', err)
    }
  }, [activeSessionId])

  // Load Preset Subjects
  const loadPresetSubjects = useCallback(async () => {
    try {
      const list = await api.getSubjects()
      setAvailableSubjects(list || [])
      if (list && list.length > 0 && !selectedPresetSubject) {
        setSelectedPresetSubject(list[0].name)
        setDiscoveredTopics(list[0].topics || [])
        setSelectedTopics(list[0].topics ? list[0].topics.slice(0, 4) : [])
      }
    } catch (err) {
      console.error('Failed to load subjects:', err)
    }
  }, [selectedPresetSubject])

  useEffect(() => {
    loadSessions()
    loadPresetSubjects()
  }, [loadSessions, loadPresetSubjects])

  // Load Active Session details & history
  const loadSessionDetails = useCallback(async (sessionId: string) => {
    if (!sessionId) return
    setLearningPlan(null)
    setLoadingPlan(true)
    setHighlights([])
    setReviewSheet(null)
    try {
      const history = await api.getHistory(sessionId)
      setMessages(history.messages || [])
      setSessionSubject(history.title || history.subject || 'Socratic Session')

      // Load session-scoped highlights
      if (history.highlights && Array.isArray(history.highlights)) {
        const mapped = history.highlights.map((h: any) => ({
          text: h.quoted_text || h.text || '',
          note: h.question || h.note || '',
          section: h.tag || h.section || 'Text Selection',
        }))
        setHighlights(mapped)
      } else {
        setHighlights([])
      }

      // If history already has a valid learning plan with modules, use it
      if (history.learning_plan && Array.isArray(history.learning_plan.modules) && history.learning_plan.modules.length > 0) {
        setLearningPlan(history.learning_plan)
        setLoadingPlan(false)
      } else {
        // Fetch or trigger plan generation
        try {
          const plan = await api.getLearningPlan(sessionId)
          if (plan && Array.isArray(plan.modules) && plan.modules.length > 0) {
            setLearningPlan(plan)
          } else {
            setLearningPlan(null)
          }
        } catch (e) {
          console.error('Failed to load learning plan:', e)
          setLearningPlan(null)
        } finally {
          setLoadingPlan(false)
        }
      }

      // Attempt to load generated textbook article quietly in background
      setArticleLoading(true)
      const tb = await api.generateTextbook(sessionId)
      setArticle(tb)
    } catch (err) {
      console.error('Error fetching session details:', err)
      setLoadingPlan(false)
    } finally {
      setArticleLoading(false)
    }
  }, [])

  useEffect(() => {
    if (activeSessionId) {
      loadSessionDetails(activeSessionId)
    }
  }, [activeSessionId, loadSessionDetails])

  // Preset Subject Selection Handler
  const handleSelectPresetSubject = (subjName: string) => {
    setSelectedPresetSubject(subjName)
    const match = availableSubjects.find((s) => s.name === subjName)
    const top = match?.topics || []
    setDiscoveredTopics(top)
    setSelectedTopics(top.slice(0, 4))
  }

  // Validate & Discover Custom Subject Handler
  const handleValidateCustomSubject = async () => {
    if (!customSubjectInput.trim()) return
    setValidatingSubject(true)
    try {
      const res = await api.validateSubject(customSubjectInput.trim())
      // Add or update in availableSubjects
      setAvailableSubjects((prev) => {
        const filtered = prev.filter((s) => s.name.toLowerCase() !== res.name.toLowerCase())
        return [res, ...filtered]
      })
      setSelectedPresetSubject(res.name)
      setDiscoveredTopics(res.topics || [])
      setSelectedTopics(res.topics ? res.topics.slice(0, 4) : [])
      setCustomSubjectInput('')
      setSubjectSource('preset')
    } catch (err) {
      console.error('Failed to validate subject:', err)
    } finally {
      setValidatingSubject(false)
    }
  }

  // Toggle Topic Selection Checkbox / Badge
  const toggleTopicSelection = (topic: string) => {
    setSelectedTopics((prev) =>
      prev.includes(topic) ? prev.filter((t) => t !== topic) : [...prev, topic]
    )
  }

  // Start New Session Handler
  const handleStartNewSession = async () => {
    const finalSubject = subjectSource === 'preset' ? selectedPresetSubject : customSubjectInput.trim()
    if (!finalSubject) return
    if (selectedTopics.length === 0) return

    setCreatingSession(true)
    try {
      const res = await api.startSession(finalSubject, selectedTopics)
      setIsNewSessionOpen(false)

      // Refresh sessions list
      await loadSessions()
      setActiveSessionId(res.session_id)
      setStageMode('chat') // Default to full Socratic chat view
      setIsDrawerOpen(true) // Ensure learning path drawer is visible

      // Auto-trigger learning plan generation immediately
      setLoadingPlan(true)
      api
        .getLearningPlan(res.session_id)
        .then((plan) => setLearningPlan(plan))
        .catch((e) => console.error('Failed to auto-generate learning plan:', e))
        .finally(() => setLoadingPlan(false))
    } catch (err) {
      console.error('Failed to start new session:', err)
    } finally {
      setCreatingSession(false)
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

  const handleGenerateLearningPlan = async () => {
    if (!activeSessionId) return
    setLoadingPlan(true)
    try {
      const plan = await api.getLearningPlan(activeSessionId)
      setLearningPlan(plan)
    } catch (err) {
      console.error('Failed to generate learning plan:', err)
    } finally {
      setLoadingPlan(false)
    }
  }

  const handleSendMessage = async (promptMsg: string) => {
    if (!activeSessionId) return
    setSendingMsg(true)
    const newMsg: ChatMessage = { role: 'user', content: promptMsg, timestamp: new Date().toISOString() }
    setMessages((prev) => [...prev, newMsg])

    try {
      const res = await api.sendMessage(activeSessionId, promptMsg)
      const botMsg: ChatMessage = {
        role: 'assistant',
        content: res.response,
        timestamp: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, botMsg])
    } catch (err) {
      console.error('Failed to send message:', err)
    } finally {
      setSendingMsg(false)
    }
  }

  const handleAskAboutSelection = (selectedText: string) => {
    const prompt = `Can you explain or elaborate on this excerpt from the text: "${selectedText}"?`
    setStageMode('chat')
    handleSendMessage(prompt)
  }

  const handleDiscussTopic = (topicPrompt: string) => {
    setStageMode('chat')
    handleSendMessage(topicPrompt)
  }

  const handleGetSocraticHint = async (question: string) => {
    if (!activeSessionId) return
    setSendingMsg(true)
    setStageMode('chat')
    try {
      const hintRes = await api.getSocraticHint(activeSessionId, question, article?.markdown_content)
      const hintText = hintRes.excerpt
        ? `**Socratic Hint**: ${hintRes.hint}\n\n*Relevant Excerpt*: "${hintRes.excerpt}"`
        : `**Socratic Hint**: ${hintRes.hint}`
      const botMsg: ChatMessage = { role: 'assistant', content: hintText, timestamp: new Date().toISOString() }
      setMessages((prev) => [...prev, botMsg])
    } catch (err) {
      console.error('Failed to get socratic hint:', err)
    } finally {
      setSendingMsg(false)
    }
  }

  const handleAddHighlight = async (highlight: { text: string; note?: string; section?: string }) => {
    setHighlights((prev) => [...prev, highlight])
    if (activeSessionId) {
      try {
        await api.addHighlight(activeSessionId, {
          element_id: 'selection',
          quoted_text: highlight.text,
          question: highlight.note || '',
          tag: highlight.section || 'Note',
        })
      } catch (err) {
        console.error('Failed to persist highlight to session:', err)
      }
    }
  }

  const handleRemoveHighlight = async (index: number) => {
    setHighlights((prev) => prev.filter((_, i) => i !== index))
    if (activeSessionId) {
      try {
        await api.deleteHighlight(activeSessionId, index)
      } catch (err) {
        console.error('Failed to delete highlight from session:', err)
      }
    }
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
      {/* Session Navigation & Stage Mode Bar */}
      <div className="flex items-center justify-between px-4 py-1.5 border-b bg-muted/30 text-xs gap-2">
        <div className="flex items-center gap-2 overflow-x-auto">
          <Select value={activeSessionId} onValueChange={setActiveSessionId}>
            <SelectTrigger className="w-[240px] sm:w-[300px] h-7 text-xs bg-background border-border/60 rounded-md shadow-xs">
              <SelectValue placeholder="Select session" />
            </SelectTrigger>
            <SelectContent className="max-w-[420px]">
              {sessions.map((s) => (
                <SelectItem key={s.id} value={s.id} className="text-xs">
                  <div className="flex flex-col text-left py-0.5 max-w-[380px]">
                    <span className="font-medium truncate text-foreground">{s.title || s.subject}</span>
                    {s.created_at && (
                      <span className="text-[10px] text-muted-foreground">
                        {new Date(s.created_at).toLocaleDateString([], {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    )}
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Button size="sm" variant="outline" className="h-7 text-xs cursor-pointer rounded-md" onClick={() => setIsNewSessionOpen(true)}>
            <Plus className="h-3.5 w-3.5 mr-1" /> New Session
          </Button>

          {/* Primary View Switcher: Reader vs Big Socratic Chat */}
          <div className="flex items-center border rounded-md bg-background p-0.5 shadow-2xs ml-1">
            <button
              onClick={() => setStageMode('reader')}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium transition-colors cursor-pointer ${
                stageMode === 'reader'
                  ? 'bg-primary text-primary-foreground shadow-xs'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <BookOpen className="h-3.5 w-3.5" />
              <span>Reader</span>
            </button>
            <button
              onClick={() => setStageMode('chat')}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium transition-colors cursor-pointer ${
                stageMode === 'chat'
                  ? 'bg-primary text-primary-foreground shadow-xs'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <MessageSquare className="h-3.5 w-3.5" />
              <span>Chat</span>
              {messages.length > 0 && (
                <span
                  className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${
                    stageMode === 'chat'
                      ? 'bg-primary-foreground/20 text-primary-foreground'
                      : 'bg-muted text-muted-foreground'
                  }`}
                >
                  {messages.length}
                </span>
              )}
            </button>
          </div>
        </div>

        {/* Drawer Desktop Toggle & Mobile Sheet Trigger */}
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            className="hidden md:flex items-center gap-1.5 h-7 text-xs cursor-pointer"
            onClick={() => setIsDrawerOpen(!isDrawerOpen)}
          >
            {isDrawerOpen ? (
              <>
                <PanelRightClose className="h-3.5 w-3.5" /> Collapse
              </>
            ) : (
              <>
                <PanelRightOpen className="h-3.5 w-3.5 text-primary" /> Learning Path
              </>
            )}
          </Button>

          {/* Mobile Viewport Sheet Trigger */}
          <div className="md:hidden">
            <Sheet open={mobileDrawerOpen} onOpenChange={setMobileDrawerOpen}>
              <SheetTrigger asChild>
                <Button size="sm" className="h-7 text-xs">
                  <Compass className="h-3.5 w-3.5 mr-1" /> Path
                </Button>
              </SheetTrigger>
              <SheetContent side="right" className="w-full sm:max-w-md p-0">
                <SheetHeader className="p-4 pb-0">
                  <SheetTitle className="text-sm font-bold flex items-center gap-2">
                    <Compass className="h-4 w-4 text-primary" /> Learning Path & Companion
                  </SheetTitle>
                </SheetHeader>
                <div className="h-[calc(100vh-4rem)]">
                  <CompanionTutorDrawer
                    learningPlan={learningPlan}
                    loadingPlan={loadingPlan}
                    onGenerateLearningPlan={handleGenerateLearningPlan}
                    onDiscussTopic={handleDiscussTopic}
                    onGetSocraticHint={handleGetSocraticHint}
                    highlights={highlights}
                    onRemoveHighlight={handleRemoveHighlight}
                    onCompileReviewSheet={handleCompileReviewSheet}
                    reviewSheet={reviewSheet}
                    compilingSheet={compilingSheet}
                    sessionSubject={sessionSubject}
                  />
                </div>
              </SheetContent>
            </Sheet>
          </div>
        </div>
      </div>

      {/* Dual-Pane Workspace Core Stage */}
      <div className="flex-1 flex overflow-hidden">
        {/* Primary Stage: Socratic Reader OR Big Chat */}
        {stageMode === 'chat' ? (
          <BigChatView
            messages={messages}
            sending={sendingMsg}
            sessionSubject={sessionSubject}
            onSendMessage={handleSendMessage}
            onOpenQuizModal={() => setIsQuizOpen(true)}
            onGenerateCertificate={() => setIsCertOpen(true)}
          />
        ) : (
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
        )}

        {/* Collapsible Socratic Companion Drawer (Learning Path, Highlights, Review Sheet) */}
        {isDrawerOpen && (
          <div className="hidden md:block w-[380px] lg:w-[440px] shrink-0 h-full transition-all duration-300">
            <CompanionTutorDrawer
              learningPlan={learningPlan}
              loadingPlan={loadingPlan}
              onGenerateLearningPlan={handleGenerateLearningPlan}
              onDiscussTopic={handleDiscussTopic}
              onGetSocraticHint={handleGetSocraticHint}
              highlights={highlights}
              onRemoveHighlight={handleRemoveHighlight}
              onCompileReviewSheet={handleCompileReviewSheet}
              reviewSheet={reviewSheet}
              compilingSheet={compilingSheet}
              sessionSubject={sessionSubject}
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

      {/* New Session Creation Dialog with Preset Dropdown, Custom Validation & Multi-topic Selection */}
      <Dialog open={isNewSessionOpen} onOpenChange={setIsNewSessionOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-base font-bold">Start New Learning Session</DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-2">
            {/* Subject Source Toggle: Preset vs Custom */}
            <div className="flex items-center gap-4 text-xs">
              <span className="font-medium text-muted-foreground">Subject Source:</span>
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="radio"
                    name="subjectSource"
                    checked={subjectSource === 'preset'}
                    onChange={() => setSubjectSource('preset')}
                    className="accent-primary"
                  />
                  <span>Preset Subjects</span>
                </label>
                <label className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="radio"
                    name="subjectSource"
                    checked={subjectSource === 'custom'}
                    onChange={() => setSubjectSource('custom')}
                    className="accent-primary"
                  />
                  <span>Custom (Discover with AI)</span>
                </label>
              </div>
            </div>

            {/* Source = Preset */}
            {subjectSource === 'preset' ? (
              <div className="space-y-2">
                <label className="text-xs font-semibold">Select Subject</label>
                {availableSubjects.length > 0 ? (
                  <Select value={selectedPresetSubject} onValueChange={handleSelectPresetSubject}>
                    <SelectTrigger className="w-full text-xs">
                      <SelectValue placeholder="Choose a subject..." />
                    </SelectTrigger>
                    <SelectContent>
                      {availableSubjects.map((s) => (
                        <SelectItem key={s.id || s.name} value={s.name} className="text-xs">
                          {s.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <div className="text-xs text-muted-foreground p-3 border rounded-md bg-muted/20">
                    No preset subjects available in the database yet. Select 'Custom' to generate one.
                  </div>
                )}
              </div>
            ) : (
              /* Source = Custom */
              <div className="space-y-2">
                <label className="text-xs font-semibold">Enter Custom Subject Name</label>
                <div className="flex gap-2">
                  <Input
                    placeholder="e.g. Next.js App Router, Golang Concurrency, System Design"
                    value={customSubjectInput}
                    onChange={(e) => setCustomSubjectInput(e.target.value)}
                    className="text-xs"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault()
                        handleValidateCustomSubject()
                      }
                    }}
                  />
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    className="text-xs shrink-0 cursor-pointer"
                    onClick={handleValidateCustomSubject}
                    disabled={validatingSubject || !customSubjectInput.trim()}
                  >
                    {validatingSubject ? 'Discovering...' : 'Validate & Discover'}
                  </Button>
                </div>
                <p className="text-[11px] text-muted-foreground">
                  Our AI normalizes the subject, generates core curriculum topics, and saves them to the database for future sessions.
                </p>
              </div>
            )}

            {/* Topics Multi-Selection Badges */}
            <div className="space-y-2 pt-2 border-t">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold">
                  Focus Topics ({selectedTopics.length} selected)
                </label>
                {discoveredTopics.length > 0 && (
                  <button
                    type="button"
                    onClick={() =>
                      setSelectedTopics(
                        selectedTopics.length === discoveredTopics.length ? [] : [...discoveredTopics]
                      )
                    }
                    className="text-[11px] text-primary hover:underline cursor-pointer"
                  >
                    {selectedTopics.length === discoveredTopics.length ? 'Deselect All' : 'Select All'}
                  </button>
                )}
              </div>

              {discoveredTopics.length > 0 ? (
                <div className="flex flex-wrap gap-1.5 p-3 rounded-lg border bg-muted/10 max-h-48 overflow-y-auto">
                  {discoveredTopics.map((topic, idx) => {
                    const isSelected = selectedTopics.includes(topic)
                    return (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => toggleTopicSelection(topic)}
                        className={`text-xs px-2.5 py-1 rounded-md border transition-colors cursor-pointer flex items-center gap-1.5 ${
                          isSelected
                            ? 'bg-primary text-primary-foreground border-primary font-medium shadow-2xs'
                            : 'bg-background text-muted-foreground hover:text-foreground border-border'
                        }`}
                      >
                        <span className={`w-2 h-2 rounded-full ${isSelected ? 'bg-primary-foreground' : 'bg-muted-foreground/40'}`} />
                        <span>{topic}</span>
                      </button>
                    )
                  })}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground italic py-2">
                  Select a subject or discover a custom subject to load topics.
                </p>
              )}
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setIsNewSessionOpen(false)} disabled={creatingSession}>
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={handleStartNewSession}
              disabled={
                creatingSession ||
                selectedTopics.length === 0 ||
                (subjectSource === 'preset' ? !selectedPresetSubject : !customSubjectInput.trim() && discoveredTopics.length === 0)
              }
              className="cursor-pointer"
            >
              {creatingSession ? 'Initializing Session...' : 'Start Learning Session'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
