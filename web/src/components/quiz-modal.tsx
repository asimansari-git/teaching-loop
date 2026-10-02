import { useState } from 'react'
import { api } from '@/api/client'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { CheckCircle2, XCircle, Loader2, Award } from 'lucide-react'

interface QuizModalProps {
  isOpen: boolean
  onClose: () => void
  sessionId: string
}

export function QuizModal({ isOpen, onClose, sessionId }: QuizModalProps) {
  const [difficulty, setDifficulty] = useState<'easy' | 'mid' | 'hard'>('easy')
  const [quizData, setQuizData] = useState<any>(null)
  const [loading, setLoading] = useState<boolean>(false)
  const [userAnswers, setUserAnswers] = useState<Record<string, number>>({})
  const [submitting, setSubmitting] = useState<boolean>(false)
  const [quizResult, setQuizResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  const handleGenerateQuiz = async (selectedDiff: 'easy' | 'mid' | 'hard') => {
    setDifficulty(selectedDiff)
    if (!sessionId) {
      setError('Please select or create an active session first before generating an assessment.')
      return
    }
    setLoading(true)
    setError(null)
    setQuizResult(null)
    setUserAnswers({})
    try {
      const data = await api.generateQuiz(sessionId, selectedDiff)
      setQuizData(data)
    } catch (err: any) {
      setError(err.message || 'Failed to generate quiz')
    } finally {
      setLoading(false)
    }
  }

  const handleSelectAnswer = (qIndex: number, optionIndex: number) => {
    setUserAnswers((prev) => ({ ...prev, [String(qIndex)]: optionIndex }))
  }

  const handleSubmitQuiz = async () => {
    if (!quizData) return
    setSubmitting(true)
    setError(null)
    try {
      const quizId = quizData.db_id || quizData.id
      const res = await api.submitQuiz(quizId, userAnswers)
      setQuizResult(res)
    } catch (err: any) {
      setError(err.message || 'Failed to evaluate quiz')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-lg">
            <CheckCircle2 className="h-5 w-5 text-emerald-500" />
            Socratic Assessment Quiz
          </DialogTitle>
          <DialogDescription>
            Test your understanding across difficulty levels.
          </DialogDescription>
        </DialogHeader>

        {/* Level Selectors */}
        <div className="flex gap-2 my-2">
          {(['easy', 'mid', 'hard'] as const).map((diff) => (
            <Button
              key={diff}
              variant={difficulty === diff ? 'default' : 'outline'}
              size="sm"
              onClick={() => handleGenerateQuiz(diff)}
              disabled={loading}
              className="capitalize"
            >
              {diff} Level
            </Button>
          ))}
        </div>

        {error && (
          <div className="p-3 bg-destructive/15 text-destructive rounded-md text-xs">
            {error}
          </div>
        )}

        {loading ? (
          <div className="py-12 flex flex-col items-center justify-center space-y-3">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <p className="text-xs text-muted-foreground">Generating questions...</p>
          </div>
        ) : quizResult ? (
          <div className="space-y-4 py-4">
            <Card className={quizResult.passed ? 'border-emerald-500/50 bg-emerald-500/5' : 'border-destructive/50 bg-destructive/5'}>
              <CardContent className="p-6 text-center space-y-2">
                <div className="inline-flex p-3 rounded-full bg-background shadow-xs">
                  {quizResult.passed ? (
                    <Award className="h-8 w-8 text-emerald-500" />
                  ) : (
                    <XCircle className="h-8 w-8 text-destructive" />
                  )}
                </div>
                <h3 className="text-xl font-bold">
                  Score: {quizResult.percentage ? quizResult.percentage.toFixed(1) : quizResult.score}%
                </h3>
                <Badge variant={quizResult.passed ? 'default' : 'destructive'}>
                  {quizResult.passed ? 'Passed (>= 70%)' : 'Needs Review'}
                </Badge>
                {quizResult.feedback && (
                  <p className="text-xs text-muted-foreground mt-2">{quizResult.feedback}</p>
                )}
              </CardContent>
            </Card>

            <Button className="w-full" onClick={() => setQuizResult(null)}>
              Try Again / Change Level
            </Button>
          </div>
        ) : quizData && quizData.questions ? (
          <div className="space-y-6 py-2">
            {quizData.questions.map((q: any, qIdx: number) => (
              <Card key={qIdx} className="p-4 space-y-3 bg-card border border-border shadow-xs">
                <p className="font-semibold text-sm text-foreground">
                  {qIdx + 1}. {q.text || q.question || q.prompt || 'Question'}
                </p>
                <div className="space-y-2">
                  {(q.options || []).map((opt: string, optIdx: number) => {
                    const isSelected = userAnswers[String(qIdx)] === optIdx
                    return (
                      <button
                        key={optIdx}
                        type="button"
                        onClick={() => handleSelectAnswer(qIdx, optIdx)}
                        className={`w-full text-left p-2.5 rounded-md text-xs transition-colors border ${
                          isSelected
                            ? 'bg-primary text-primary-foreground border-primary font-medium'
                            : 'bg-card text-card-foreground hover:bg-muted border-border'
                        }`}
                      >
                        <span className="font-semibold mr-1.5">{String.fromCharCode(65 + optIdx)}.</span> {opt}
                      </button>
                    )
                  })}
                </div>
              </Card>
            ))}

            <Button
              className="w-full"
              onClick={handleSubmitQuiz}
              disabled={submitting || Object.keys(userAnswers).length < quizData.questions.length}
            >
              {submitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Evaluating Answers...
                </>
              ) : (
                'Submit Quiz'
              )}
            </Button>
          </div>
        ) : (
          <div className="py-8 text-center text-xs text-muted-foreground">
            Select a difficulty level above to begin the Socratic Quiz assessment.
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
