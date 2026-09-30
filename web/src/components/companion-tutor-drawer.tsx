import { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import {
  MessageSquare,
  Send,
  Sparkles,
  Bot,
  User as UserIcon,
  HelpCircle,
  FileText,
  Trash2,
  ListCheck,
  ChevronRight,
  Loader2,
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { ChatMessage, ReviewSheet } from '@/api/client'

interface CompanionTutorDrawerProps {
  messages: ChatMessage[]
  sending: boolean
  onSendMessage: (msg: string) => void
  onGetSocraticHint: (question: string) => void
  highlights: Array<{ text: string; note?: string; section?: string }>
  onRemoveHighlight: (index: number) => void
  onCompileReviewSheet: () => void
  reviewSheet: ReviewSheet | null
  compilingSheet: boolean
}

export function CompanionTutorDrawer({
  messages,
  sending,
  onSendMessage,
  onGetSocraticHint,
  highlights,
  onRemoveHighlight,
  onCompileReviewSheet,
  reviewSheet,
  compilingSheet,
}: CompanionTutorDrawerProps) {
  const [inputMsg, setInputMsg] = useState('')
  const [hintQuestion, setHintQuestion] = useState('')
  const [activeTab, setActiveTab] = useState<'chat' | 'highlights' | 'summary'>('chat')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending])

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputMsg.trim() || sending) return
    onSendMessage(inputMsg.trim())
    setInputMsg('')
  }

  const handleHintSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!hintQuestion.trim()) return
    onGetSocraticHint(hintQuestion.trim())
    setHintQuestion('')
  }

  return (
    <div className="h-full flex flex-col bg-card border-l border-border">
      {/* Drawer Header */}
      <div className="p-4 border-b border-border flex items-center justify-between bg-muted/30">
        <div className="flex items-center gap-2 font-semibold">
          <Bot className="h-5 w-5 text-primary" />
          <span>Socratic Companion</span>
        </div>
        <Badge variant="secondary" className="text-xs">
          Live AI Assistant
        </Badge>
      </div>

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)} className="flex-1 flex flex-col min-h-0">
        <div className="px-4 pt-2 border-b border-border bg-muted/10">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="chat" className="text-xs">
              <MessageSquare className="h-3.5 w-3.5 mr-1" />
              Tutor
            </TabsTrigger>
            <TabsTrigger value="highlights" className="text-xs">
              <Sparkles className="h-3.5 w-3.5 mr-1" />
              Highlights ({highlights.length})
            </TabsTrigger>
            <TabsTrigger value="summary" className="text-xs">
              <FileText className="h-3.5 w-3.5 mr-1" />
              Summary
            </TabsTrigger>
          </TabsList>
        </div>

        {/* Tab 1: Live Socratic Chat */}
        <TabsContent value="chat" className="flex-1 flex flex-col p-0 m-0 min-h-0">
          {/* Socratic Hint Quick Box */}
          <div className="p-3 bg-primary/5 border-b border-border">
            <form onSubmit={handleHintSubmit} className="flex gap-2">
              <Input
                placeholder="Ask Socratic Hint (e.g., Where does it talk about...?)"
                value={hintQuestion}
                onChange={(e) => setHintQuestion(e.target.value)}
                className="text-xs h-8"
              />
              <Button type="submit" size="sm" variant="outline" className="h-8 text-xs shrink-0">
                <HelpCircle className="h-3.5 w-3.5 mr-1 text-primary" />
                Find Hint
              </Button>
            </form>
          </div>

          {/* Messages Stream */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground text-xs space-y-2">
                <Bot className="h-8 w-8 mx-auto opacity-40" />
                <p>No messages yet. Ask the Socratic Tutor a question to begin guided learning.</p>
              </div>
            ) : (
              messages.map((msg, idx) => {
                const isUser = msg.role === 'user'
                return (
                  <div
                    key={idx}
                    className={`flex items-start gap-2.5 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
                  >
                    <div
                      className={`flex h-7 w-7 shrink-0 select-none items-center justify-center rounded-full text-xs font-semibold ${
                        isUser ? 'bg-primary text-primary-foreground' : 'bg-muted text-foreground'
                      }`}
                    >
                      {isUser ? <UserIcon className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5 text-primary" />}
                    </div>
                    <div
                      className={`rounded-lg px-3.5 py-2.5 text-xs max-w-[85%] leading-relaxed ${
                        isUser
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-muted/70 text-foreground border border-border/50'
                      }`}
                    >
                      {isUser ? (
                        msg.content
                      ) : (
                        <div className="prose dark:prose-invert prose-xs max-w-none">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                        </div>
                      )}
                    </div>
                  </div>
                )
              })
            )}

            {sending && (
              <div className="flex items-center gap-2 text-xs text-muted-foreground p-2 animate-pulse">
                <Bot className="h-4 w-4 animate-bounce text-primary" />
                <span>Socratic AI is thinking...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Chat Input Bar */}
          <form onSubmit={handleSend} className="p-3 border-t border-border bg-background flex gap-2">
            <Input
              placeholder="Ask a question..."
              value={inputMsg}
              onChange={(e) => setInputMsg(e.target.value)}
              disabled={sending}
              className="text-xs"
            />
            <Button type="submit" size="sm" disabled={sending || !inputMsg.trim()} className="shrink-0">
              <Send className="h-3.5 w-3.5" />
            </Button>
          </form>
        </TabsContent>

        {/* Tab 2: Saved Highlights */}
        <TabsContent value="highlights" className="flex-1 flex flex-col p-4 m-0 min-h-0 overflow-y-auto space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold">Reader Highlights</h3>
            <Button
              size="sm"
              onClick={onCompileReviewSheet}
              disabled={compilingSheet || highlights.length === 0}
            >
              {compilingSheet ? (
                <>
                  <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> Compiling...
                </>
              ) : (
                <>
                  <ListCheck className="mr-1.5 h-3.5 w-3.5" /> Compile Review Sheet
                </>
              )}
            </Button>
          </div>

          {highlights.length === 0 ? (
            <Card className="border-dashed bg-muted/20">
              <CardContent className="p-6 text-center text-xs text-muted-foreground">
                Highlight text in the primary Socratic Reader to save excerpts and generate batch review sheets.
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-2.5">
              {highlights.map((h, idx) => (
                <Card key={idx} className="relative group p-3 text-xs bg-muted/40">
                  <p className="italic text-foreground border-l-2 border-primary pl-2.5 my-1">
                    "{h.text}"
                  </p>
                  <Button
                    size="icon"
                    variant="ghost"
                    className="absolute top-2 right-2 h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity text-destructive hover:bg-destructive/10"
                    onClick={() => onRemoveHighlight(idx)}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* Tab 3: Review Sheet & Batch Summary */}
        <TabsContent value="summary" className="flex-1 flex flex-col p-4 m-0 min-h-0 overflow-y-auto space-y-4">
          {reviewSheet ? (
            <div className="space-y-4 text-xs">
              <Card>
                <CardHeader className="p-4 pb-2">
                  <CardTitle className="text-sm font-bold flex items-center gap-2">
                    <FileText className="h-4 w-4 text-primary" /> Socratic Summary
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-4 pt-0 leading-relaxed text-muted-foreground">
                  {reviewSheet.summary}
                </CardContent>
              </Card>

              {reviewSheet.key_points && reviewSheet.key_points.length > 0 && (
                <Card>
                  <CardHeader className="p-4 pb-2">
                    <CardTitle className="text-sm font-bold">Key Takeaways</CardTitle>
                  </CardHeader>
                  <CardContent className="p-4 pt-0 space-y-1.5">
                    {reviewSheet.key_points.map((kp, idx) => (
                      <div key={idx} className="flex items-start gap-2">
                        <ChevronRight className="h-3.5 w-3.5 text-primary shrink-0 mt-0.5" />
                        <span>{kp}</span>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}

              {reviewSheet.action_items && reviewSheet.action_items.length > 0 && (
                <Card>
                  <CardHeader className="p-4 pb-2">
                    <CardTitle className="text-sm font-bold">Recommended Action Items</CardTitle>
                  </CardHeader>
                  <CardContent className="p-4 pt-0 space-y-1.5">
                    {reviewSheet.action_items.map((ai, idx) => (
                      <div key={idx} className="flex items-start gap-2">
                        <Badge variant="outline" className="text-[10px] shrink-0">
                          Step {idx + 1}
                        </Badge>
                        <span>{ai}</span>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}
            </div>
          ) : (
            <Card className="border-dashed bg-muted/20">
              <CardContent className="p-6 text-center text-xs text-muted-foreground">
                No review summary compiled yet. Add highlights and click 'Compile Review Sheet' to generate key takeaways and action items.
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
