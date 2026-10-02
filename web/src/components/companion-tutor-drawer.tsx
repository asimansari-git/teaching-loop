import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import {
  MapPin,
  Sparkles,
  FileText,
  Trash2,
  ListCheck,
  ChevronRight,
  Loader2,
  Compass,
  CheckCircle2,
  Search,
  MessageSquare,
} from 'lucide-react'
import type { ReviewSheet, LearningPlan, LearningModule } from '@/api/client'

interface CompanionTutorDrawerProps {
  learningPlan: LearningPlan | null
  loadingPlan: boolean
  onGenerateLearningPlan?: () => void
  onDiscussTopic?: (topic: string) => void
  onGetSocraticHint: (question: string) => void
  highlights: Array<{ text: string; note?: string; section?: string }>
  onRemoveHighlight: (index: number) => void
  onCompileReviewSheet: () => void
  reviewSheet: ReviewSheet | null
  compilingSheet: boolean
  sessionSubject: string
}

export function CompanionTutorDrawer({
  learningPlan,
  loadingPlan,
  onGenerateLearningPlan,
  onDiscussTopic,
  onGetSocraticHint,
  highlights,
  onRemoveHighlight,
  onCompileReviewSheet,
  reviewSheet,
  compilingSheet,
  sessionSubject,
}: CompanionTutorDrawerProps) {
  const [hintQuestion, setHintQuestion] = useState('')
  const [activeTab, setActiveTab] = useState<'path' | 'highlights' | 'summary'>('path')

  const handleHintSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!hintQuestion.trim()) return
    onGetSocraticHint(hintQuestion.trim())
    setHintQuestion('')
  }

  const modules: LearningModule[] = learningPlan?.modules || []

  return (
    <div className="flex flex-col h-full bg-card/50 border-l border-border">
      {/* Drawer Header with Inverted Retrieval Socratic Locator */}
      <div className="p-3.5 border-b bg-muted/20 shrink-0 space-y-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Compass className="h-4 w-4 text-primary" />
            <h3 className="font-semibold text-sm">Socratic Companion</h3>
          </div>
          <Badge variant="outline" className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5">
            Path & Insights
          </Badge>
        </div>

        {/* Quick Socratic Hint Inverted Retrieval Search */}
        <form onSubmit={handleHintSubmit} className="flex gap-1.5">
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
            <Input
              value={hintQuestion}
              onChange={(e) => setHintQuestion(e.target.value)}
              placeholder="Ask Socratic Hint (e.g. Where is...)"
              className="h-8 text-xs pl-8 bg-background shadow-2xs"
            />
          </div>
          <Button type="submit" size="sm" variant="secondary" className="h-8 text-xs shrink-0 px-2.5">
            Find Hint
          </Button>
        </form>
      </div>

      {/* Tabs Switcher: Learning Path, Highlights, Review Sheet */}
      <Tabs
        value={activeTab}
        onValueChange={(val) => setActiveTab(val as 'path' | 'highlights' | 'summary')}
        className="flex-1 flex flex-col min-h-0"
      >
        <div className="px-3.5 pt-2.5 border-b shrink-0 bg-muted/10">
          <TabsList className="grid grid-cols-3 h-8 text-xs w-full">
            <TabsTrigger value="path" className="text-xs gap-1.5">
              <MapPin className="h-3.5 w-3.5" /> Path
            </TabsTrigger>
            <TabsTrigger value="highlights" className="text-xs gap-1.5">
              <Sparkles className="h-3.5 w-3.5 text-amber-500" /> Highlights ({highlights.length})
            </TabsTrigger>
            <TabsTrigger value="summary" className="text-xs gap-1.5">
              <FileText className="h-3.5 w-3.5" /> Summary
            </TabsTrigger>
          </TabsList>
        </div>

        {/* Tab 1: The Interactive Learning Path */}
        <TabsContent value="path" className="flex-1 overflow-y-auto p-3.5 m-0 space-y-3">
          {loadingPlan ? (
            <div className="flex flex-col items-center justify-center h-48 space-y-3 text-center">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
              <p className="text-xs text-muted-foreground">Architecting customized learning roadmap...</p>
            </div>
          ) : modules.length > 0 ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs text-muted-foreground px-0.5">
                <span>{modules.length} Modules in Sequence</span>
                {onGenerateLearningPlan && (
                  <button
                    onClick={onGenerateLearningPlan}
                    className="text-primary hover:underline text-[11px] cursor-pointer"
                  >
                    Refresh Path
                  </button>
                )}
              </div>

              {modules.map((mod, idx) => (
                <Card
                  key={idx}
                  className="border transition-all hover:border-primary/40 hover:shadow-xs group overflow-hidden"
                >
                  <CardHeader className="p-3 pb-2 space-y-1">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="flex items-center justify-center w-5 h-5 rounded-full bg-primary/10 text-primary text-[11px] font-bold shrink-0">
                          {idx + 1}
                        </span>
                        <CardTitle className="text-xs font-semibold leading-tight line-clamp-1">
                          {mod.title}
                        </CardTitle>
                      </div>
                    </div>
                    {mod.description && (
                      <CardDescription className="text-[11px] leading-relaxed text-muted-foreground pl-7 line-clamp-2">
                        {mod.description}
                      </CardDescription>
                    )}
                  </CardHeader>

                  <CardContent className="p-3 pt-0 pl-7 space-y-2">
                    {mod.topics && mod.topics.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {mod.topics.map((t, tIdx) => (
                          <Badge
                            key={tIdx}
                            variant="secondary"
                            className="text-[10px] px-1.5 py-0 bg-muted/60 font-normal hover:bg-primary/10 hover:text-primary transition-colors cursor-pointer"
                            onClick={() => onDiscussTopic?.(`Let's explore topic: "${t}" from Module ${idx + 1}: ${mod.title}`)}
                          >
                            {t}
                          </Badge>
                        ))}
                      </div>
                    )}

                    {onDiscussTopic && (
                      <Button
                        size="sm"
                        variant="ghost"
                        className="w-full h-6 text-[11px] text-primary justify-between px-2 hover:bg-primary/10"
                        onClick={() =>
                          onDiscussTopic(
                            `Please guide me through Module ${idx + 1}: "${mod.title}". What are the first principles I need to know?`
                          )
                        }
                      >
                        <span className="flex items-center gap-1">
                          <MessageSquare className="h-3 w-3" /> Discuss with Tutor
                        </span>
                        <ChevronRight className="h-3 w-3 text-muted-foreground group-hover:translate-x-0.5 transition-transform" />
                      </Button>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Card className="border-dashed border-2 bg-muted/10 my-4 text-center p-5 space-y-3">
              <div className="p-2.5 rounded-full bg-primary/10 text-primary w-fit mx-auto">
                <MapPin className="h-5 w-5" />
              </div>
              <div className="space-y-1">
                <h4 className="text-xs font-semibold">No Learning Path Generated</h4>
                <p className="text-[11px] text-muted-foreground">
                  Build a structured roadmap covering prerequisite concepts and core modules for {sessionSubject}.
                </p>
              </div>
              {onGenerateLearningPlan && (
                <Button size="sm" onClick={onGenerateLearningPlan} className="text-xs h-7 gap-1">
                  <Sparkles className="h-3.5 w-3.5" />
                  Generate Learning Path
                </Button>
              )}
            </Card>
          )}
        </TabsContent>

        {/* Tab 2: Reader Highlights & Excerpts */}
        <TabsContent value="highlights" className="flex-1 overflow-y-auto p-3.5 m-0 space-y-3">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Reader Highlights</span>
            <Button
              size="sm"
              variant="outline"
              className="h-6 text-[11px]"
              onClick={onCompileReviewSheet}
              disabled={highlights.length === 0 || compilingSheet}
            >
              {compilingSheet ? (
                <>
                  <Loader2 className="h-3 w-3 animate-spin mr-1" /> Compiling...
                </>
              ) : (
                <>
                  <ListCheck className="h-3 w-3 mr-1 text-emerald-500" /> Compile Review Sheet
                </>
              )}
            </Button>
          </div>

          {highlights.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-48 text-center text-xs text-muted-foreground space-y-2 p-4">
              <Sparkles className="h-8 w-8 text-muted/50" />
              <p>Highlight text in the textbook reader to save excerpts and generate batch review sheets.</p>
            </div>
          ) : (
            highlights.map((hl, idx) => (
              <Card key={idx} className="p-2.5 text-xs space-y-1.5 relative group border bg-card">
                <p className="italic text-foreground border-l-2 border-amber-500 pl-2 text-xs">
                  "{hl.text}"
                </p>
                {hl.note && <p className="text-muted-foreground text-[11px] pl-2">{hl.note}</p>}
                <div className="flex justify-between items-center pt-1 border-t text-[10px] text-muted-foreground">
                  <span>{hl.section || 'Text Selection'}</span>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-5 w-5 text-muted-foreground hover:text-destructive cursor-pointer"
                    onClick={() => onRemoveHighlight(idx)}
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              </Card>
            ))
          )}
        </TabsContent>

        {/* Tab 3: Compiled Review Sheet */}
        <TabsContent value="summary" className="flex-1 overflow-y-auto p-3.5 m-0 space-y-3">
          {reviewSheet ? (
            <div className="space-y-4 text-xs">
              <div className="p-3 bg-muted/40 rounded-lg space-y-1.5 border">
                <h4 className="font-semibold text-xs text-primary flex items-center gap-1.5">
                  <FileText className="h-3.5 w-3.5" /> Session Synthesis
                </h4>
                <p className="text-muted-foreground leading-relaxed text-[11px]">{reviewSheet.summary}</p>
              </div>

              {reviewSheet.key_points && reviewSheet.key_points.length > 0 && (
                <div className="space-y-1.5">
                  <h4 className="font-semibold text-xs flex items-center gap-1.5 text-emerald-500">
                    <CheckCircle2 className="h-3.5 w-3.5" /> Key Principles
                  </h4>
                  <ul className="space-y-1 pl-4 list-disc text-muted-foreground text-[11px]">
                    {reviewSheet.key_points.map((pt, i) => (
                      <li key={i}>{pt}</li>
                    ))}
                  </ul>
                </div>
              )}

              {reviewSheet.action_items && reviewSheet.action_items.length > 0 && (
                <div className="space-y-1.5">
                  <h4 className="font-semibold text-xs flex items-center gap-1.5 text-amber-500">
                    <Sparkles className="h-3.5 w-3.5" /> Recommended Next Steps
                  </h4>
                  <ul className="space-y-1 pl-4 list-disc text-muted-foreground text-[11px]">
                    {reviewSheet.action_items.map((act, i) => (
                      <li key={i}>{act}</li>
                    ))}
                  </ul>
                </div>
              )}

              <p className="text-[10px] text-muted-foreground text-center pt-2">
                Compiled at {new Date(reviewSheet.compiled_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </p>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-48 text-center text-xs text-muted-foreground space-y-2 p-4">
              <FileText className="h-8 w-8 text-muted/50" />
              <p>No review summary compiled yet. Add highlights in the Reader and click "Compile Review Sheet".</p>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
