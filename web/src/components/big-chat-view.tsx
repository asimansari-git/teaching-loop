import { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import {
  Send,
  Bot,
  User as UserIcon,
  Sparkles,
  Loader2,
  Lightbulb,
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import type { ChatMessage } from '@/api/client'

interface BigChatViewProps {
  messages: ChatMessage[]
  sending: boolean
  sessionSubject: string
  onSendMessage: (msg: string) => void
  onOpenQuizModal?: () => void
  onGenerateCertificate?: () => void
}

const SUGGESTED_PROMPTS = [
  'Explain the core concept in simple terms with a real-world analogy.',
  'Challenge me with a Socratic question to test my understanding.',
  'Show me a clean, practical code example of this in action.',
  'What are the common pitfalls or edge cases beginners face here?',
]

export function BigChatView({
  messages,
  sending,
  sessionSubject,
  onSendMessage,
  onOpenQuizModal,
  onGenerateCertificate,
}: BigChatViewProps) {
  const [inputMsg, setInputMsg] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending])

  const handleSend = (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    if (!inputMsg.trim() || sending) return
    onSendMessage(inputMsg.trim())
    setInputMsg('')
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-hidden">
      {/* Big Chat Top Header */}
      <div className="flex flex-wrap items-center justify-between px-4 md:px-6 py-2.5 border-b shrink-0 gap-3">
        <div className="flex items-center gap-2.5">
          <Bot className="h-5 w-5 text-primary" />
          <div>
            <h2 className="font-semibold text-sm leading-tight text-foreground">{sessionSubject}</h2>
            <p className="text-[11px] text-muted-foreground">
              First-principles inquiry and guided reasoning
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {onOpenQuizModal && (
            <Button variant="secondary" size="sm" onClick={onOpenQuizModal} className="text-xs gap-1.5 cursor-pointer">
              <Sparkles className="h-3.5 w-3.5 text-emerald-500" />
              Practice Quiz
            </Button>
          )}

          {onGenerateCertificate && (
            <Button variant="outline" size="sm" onClick={onGenerateCertificate} className="text-xs gap-1.5 cursor-pointer">
              <Sparkles className="h-3.5 w-3.5 text-amber-500" />
              Certificate
            </Button>
          )}
        </div>
      </div>

      {/* Main Conversation Scroll Stream */}
      <div className="flex-1 overflow-y-auto px-4 md:px-12 py-6 space-y-6">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center min-h-[400px] text-center max-w-xl mx-auto space-y-5">
            <div className="p-4 rounded-2xl bg-primary/10 text-primary shadow-xs">
              <Sparkles className="h-8 w-8" />
            </div>
            <div className="space-y-2">
              <h3 className="text-lg font-bold">Begin Socratic Exploration</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Ask any question, test hypotheses, or request first-principles breakdowns for{' '}
                <span className="font-medium text-foreground">{sessionSubject}</span>.
              </p>
            </div>

            <div className="w-full grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2">
              {SUGGESTED_PROMPTS.map((prompt, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => onSendMessage(prompt)}
                  className="text-left p-3 rounded-lg border bg-card hover:bg-accent/50 text-xs text-muted-foreground hover:text-foreground transition-colors flex items-start gap-2 shadow-2xs cursor-pointer"
                >
                  <Lightbulb className="h-3.5 w-3.5 text-amber-500 shrink-0 mt-0.5" />
                  <span>{prompt}</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((m, idx) => {
            const isUser = m.role === 'user'
            return (
              <div
                key={idx}
                className={`flex gap-3 max-w-3xl ${isUser ? 'ml-auto flex-row-reverse' : 'mr-auto'}`}
              >
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-1 ${
                    isUser
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted text-foreground border border-border shadow-2xs'
                  }`}
                >
                  {isUser ? <UserIcon className="h-4 w-4" /> : <Bot className="h-4 w-4 text-primary" />}
                </div>

                <div
                  className={`flex flex-col space-y-1.5 max-w-[85%] ${
                    isUser ? 'items-end' : 'items-start'
                  }`}
                >
                  <div className="flex items-center gap-2 text-xs text-muted-foreground px-1">
                    <span className="font-medium text-foreground">
                      {isUser ? 'You' : 'Socratic Tutor'}
                    </span>
                    {m.timestamp && (
                      <span>{new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    )}
                  </div>

                  {m.selected_text && (
                    <div className="text-xs italic bg-muted/60 border-l-2 border-primary/60 px-3 py-1.5 rounded-r-md text-muted-foreground">
                      Excerpt: "{m.selected_text}"
                    </div>
                  )}

                  <div
                    className={`rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-2xs ${
                      isUser
                        ? 'bg-primary text-primary-foreground rounded-tr-xs'
                        : 'bg-card border rounded-tl-xs prose dark:prose-invert max-w-none'
                    }`}
                  >
                    {isUser ? (
                      <p className="whitespace-pre-wrap">{m.content}</p>
                    ) : (
                      <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
                        {m.content}
                      </ReactMarkdown>
                    )}
                  </div>
                </div>
              </div>
            )
          })
        )}

        {sending && (
          <div className="flex gap-3 max-w-3xl mr-auto items-center">
            <div className="w-8 h-8 rounded-full bg-muted border flex items-center justify-center text-primary">
              <Bot className="h-4 w-4" />
            </div>
            <div className="bg-card border rounded-2xl rounded-tl-xs px-4 py-2.5 text-xs text-muted-foreground flex items-center gap-2 shadow-2xs">
              <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
              <span>Socratic AI is formulating guidance...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Spacious Bottom Message Input Bar */}
      <div className="p-4 border-t bg-card/60 backdrop-blur-xs shrink-0 max-w-4xl mx-auto w-full">
        <form onSubmit={handleSend} className="relative flex items-end gap-2">
          <textarea
            ref={inputRef}
            rows={2}
            value={inputMsg}
            onChange={(e) => setInputMsg(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Ask a question or explore a concept in ${sessionSubject}... (Enter to send, Shift+Enter for new line)`}
            className="flex-1 min-h-[52px] max-h-36 resize-none rounded-xl border border-input bg-background px-3.5 py-2.5 text-sm shadow-2xs placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            disabled={sending}
          />
          <Button
            type="submit"
            size="icon"
            className="h-[52px] w-[52px] rounded-xl shrink-0 cursor-pointer"
            disabled={!inputMsg.trim() || sending}
          >
            {sending ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
          </Button>
        </form>
      </div>
    </div>
  )
}
