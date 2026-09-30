import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { BookOpen, Sparkles, RefreshCw, MessageSquareQuote, CheckCircle2, Award } from 'lucide-react'
import type { TextbookArticle } from '@/api/client'

interface SocraticReaderProps {
  article: TextbookArticle | null
  loading: boolean
  sessionSubject: string
  onGenerateArticle: () => void
  onAskAboutSelection: (selectedText: string) => void
  onAddHighlight: (highlight: { text: string; note?: string; section?: string }) => void
  onOpenQuizModal?: () => void
  onGenerateCertificate?: () => void
}

export function SocraticReader({
  article,
  loading,
  sessionSubject,
  onGenerateArticle,
  onAskAboutSelection,
  onAddHighlight,
  onOpenQuizModal,
  onGenerateCertificate,
}: SocraticReaderProps) {
  const [selectedText, setSelectedText] = useState<string>('')
  const [selectionPosition, setSelectionPosition] = useState<{ top: number; left: number } | null>(null)
  const [fontSize, setFontSize] = useState<'normal' | 'large' | 'xlarge'>('normal')
  const contentRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleSelectionChange = () => {
      const selection = window.getSelection()
      if (!selection || selection.isCollapsed || !contentRef.current) {
        setSelectionPosition(null)
        setSelectedText('')
        return
      }

      const text = selection.toString().trim()
      if (text.length > 3 && contentRef.current.contains(selection.anchorNode)) {
        const range = selection.getRangeAt(0)
        const rect = range.getBoundingClientRect()
        const containerRect = contentRef.current.getBoundingClientRect()

        setSelectedText(text)
        setSelectionPosition({
          top: rect.top - containerRect.top - 45,
          left: Math.max(10, rect.left - containerRect.left + rect.width / 2 - 120),
        })
      } else {
        setSelectionPosition(null)
        setSelectedText('')
      }
    }

    document.addEventListener('selectionchange', handleSelectionChange)
    return () => document.removeEventListener('selectionchange', handleSelectionChange)
  }, [])

  const fontSizeClasses = {
    normal: 'prose-base',
    large: 'prose-lg',
    xlarge: 'prose-xl',
  }

  return (
    <div className="relative flex-1 h-full overflow-y-auto p-4 md:p-8 bg-background">
      {/* Floating Header Bar for Reader */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6 pb-4 border-b border-border">
        <div>
          <div className="flex items-center gap-2">
            <BookOpen className="h-5 w-5 text-primary" />
            <h1 className="text-xl font-bold tracking-tight text-foreground">
              {article ? article.title : sessionSubject || 'Socratic Reader'}
            </h1>
          </div>
          {article?.topics && article.topics.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {article.topics.map((t, idx) => (
                <Badge key={idx} variant="outline" className="text-xs">
                  {t}
                </Badge>
              ))}
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center border rounded-lg bg-muted p-0.5 text-xs">
            <button
              onClick={() => setFontSize('normal')}
              className={`px-2 py-1 rounded-md ${fontSize === 'normal' ? 'bg-background shadow-xs font-semibold' : 'text-muted-foreground'}`}
            >
              A
            </button>
            <button
              onClick={() => setFontSize('large')}
              className={`px-2 py-1 rounded-md ${fontSize === 'large' ? 'bg-background shadow-xs font-semibold' : 'text-muted-foreground'}`}
            >
              A+
            </button>
            <button
              onClick={() => setFontSize('xlarge')}
              className={`px-2 py-1 rounded-md ${fontSize === 'xlarge' ? 'bg-background shadow-xs font-semibold' : 'text-muted-foreground'}`}
            >
              A++
            </button>
          </div>

          <Button variant="outline" size="sm" onClick={onGenerateArticle} disabled={loading}>
            <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${loading ? 'animate-spin' : ''}`} />
            {article ? 'Regenerate' : 'Generate Article'}
          </Button>

          {onOpenQuizModal && (
            <Button variant="secondary" size="sm" onClick={onOpenQuizModal}>
              <CheckCircle2 className="h-3.5 w-3.5 mr-1.5 text-emerald-500" />
              Quiz
            </Button>
          )}

          {onGenerateCertificate && (
            <Button variant="outline" size="sm" onClick={onGenerateCertificate}>
              <Award className="h-3.5 w-3.5 mr-1.5 text-amber-500" />
              Certificate
            </Button>
          )}
        </div>
      </div>

      {/* Main Socratic Content Container */}
      <div ref={contentRef} className="relative min-h-[500px]">
        {/* Floating Selection Action Popup */}
        {selectionPosition && selectedText && (
          <div
            style={{ top: `${selectionPosition.top}px`, left: `${selectionPosition.left}px` }}
            className="absolute z-30 flex items-center gap-1 bg-popover text-popover-foreground border shadow-lg rounded-lg p-1 animate-in fade-in zoom-in-95 duration-150"
          >
            <Button
              size="sm"
              variant="ghost"
              className="h-7 text-xs px-2 text-primary font-medium hover:bg-primary/10"
              onClick={() => {
                onAskAboutSelection(selectedText)
                setSelectionPosition(null)
              }}
            >
              <MessageSquareQuote className="h-3.5 w-3.5 mr-1" />
              Ask Socratic AI
            </Button>
            <div className="h-4 w-px bg-border" />
            <Button
              size="sm"
              variant="ghost"
              className="h-7 text-xs px-2 hover:bg-muted"
              onClick={() => {
                onAddHighlight({ text: selectedText })
                setSelectionPosition(null)
              }}
            >
              <Sparkles className="h-3.5 w-3.5 mr-1 text-amber-500" />
              Highlight & Save
            </Button>
          </div>
        )}

        {loading ? (
          <div className="flex flex-col items-center justify-center h-80 space-y-4">
            <RefreshCw className="h-8 w-8 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground animate-pulse">
              Synthesizing Socratic Textbook Article with AI...
            </p>
          </div>
        ) : article?.markdown_content ? (
          <article className={`prose dark:prose-invert max-w-none ${fontSizeClasses[fontSize]} leading-relaxed`}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {article.markdown_content}
            </ReactMarkdown>
          </article>
        ) : (
          <Card className="border-dashed border-2 bg-muted/20 my-8">
            <CardHeader className="text-center">
              <CardTitle className="text-lg">No Socratic Article Loaded</CardTitle>
              <CardDescription>
                Click 'Generate Article' to generate an AI-tailored reading article for this subject session, or select text in the conversation pane.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex justify-center pb-6">
              <Button onClick={onGenerateArticle}>
                <Sparkles className="h-4 w-4 mr-2" />
                Generate Socratic Article
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
