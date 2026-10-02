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
import { Award, Loader2, Sparkles, AlertCircle } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface CertificateModalProps {
  isOpen: boolean
  onClose: () => void
  sessionId: string
  subject: string
}

export function CertificateModal({ isOpen, onClose, sessionId, subject }: CertificateModalProps) {
  const [loading, setLoading] = useState<boolean>(false)
  const [certificateData, setCertificateData] = useState<{
    content: string
    verification_hash: string
    created_at: string
  } | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleGenerateCertificate = async () => {
    if (!sessionId) {
      setError('Please select or create an active session first before requesting a certificate.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const data = await api.generateCertificate(sessionId, subject)
      setCertificateData(data)
    } catch (err: any) {
      setError(err.message || 'Failed to generate certificate')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-lg">
            <Award className="h-5 w-5 text-amber-500" />
            Socratic Mastery Certificate
          </DialogTitle>
          <DialogDescription>
            Earned upon passing all assessment quiz levels (Easy, Mid, and Hard &gt;= 70%).
          </DialogDescription>
        </DialogHeader>

        {error && (
          <div className="p-3 bg-destructive/15 text-destructive rounded-md text-xs flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {certificateData ? (
          <Card className="border-2 border-amber-500/40 bg-amber-500/5 my-2">
            <CardContent className="p-6 space-y-4">
              <div className="text-center border-b pb-4">
                <Award className="h-12 w-12 text-amber-500 mx-auto mb-2" />
                <span className="text-xs font-mono text-muted-foreground">
                  Verification Hash: {certificateData.verification_hash}
                </span>
              </div>
              <div className="prose dark:prose-invert max-w-none text-sm">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {certificateData.content}
                </ReactMarkdown>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="py-8 text-center space-y-4">
            <Sparkles className="h-10 w-10 text-amber-500 mx-auto animate-pulse" />
            <p className="text-xs text-muted-foreground max-w-md mx-auto">
              Request official completion certificate verified by your Socratic learning performance history.
            </p>
            <Button onClick={handleGenerateCertificate} disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Verifying & Generating...
                </>
              ) : (
                'Generate Socratic Certificate'
              )}
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
