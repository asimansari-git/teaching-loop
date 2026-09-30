import { useState, useEffect } from 'react'
import { api, type User, type ReportItem } from '@/api/client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { GraduationCap, FileText, Loader2, Calendar } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

export function TeacherDashboard() {
  const [students, setStudents] = useState<User[]>([])
  const [selectedStudentId, setSelectedStudentId] = useState<string>('')
  const [studentReports, setStudentReports] = useState<ReportItem[]>([])
  const [loading, setLoading] = useState<boolean>(false)

  useEffect(() => {
    api
      .getStudents()
      .then((data) => {
        setStudents(data)
        if (data.length > 0) {
          setSelectedStudentId(String(data[0].id))
        }
      })
      .catch((err) => console.error('Failed to load students:', err))
  }, [])

  useEffect(() => {
    if (!selectedStudentId) return
    setLoading(true)
    api
      .getStudentReports(Number(selectedStudentId))
      .then(setStudentReports)
      .catch((err) => console.error('Failed to load reports:', err))
      .finally(() => setLoading(false))
  }, [selectedStudentId])

  const selectedStudent = students.find((s) => String(s.id) === selectedStudentId)

  return (
    <div className="container mx-auto p-4 md:p-8 space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b pb-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <GraduationCap className="h-7 w-7 text-primary" /> Teacher Overview Dashboard
          </h1>
          <p className="text-sm text-muted-foreground">
            Monitor student progress, analyze performance assessments, and generate batch summary reports.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <label className="text-xs font-medium shrink-0">Select Student:</label>
          <Select value={selectedStudentId} onValueChange={setSelectedStudentId}>
            <SelectTrigger className="w-[200px] h-9 text-xs">
              <SelectValue placeholder="Select student" />
            </SelectTrigger>
            <SelectContent>
              {students.map((s) => (
                <SelectItem key={s.id} value={String(s.id)}>
                  {s.username}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {selectedStudent && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Student Info Card */}
          <Card className="md:col-span-1">
            <CardHeader className="p-4 pb-2">
              <CardTitle className="text-base font-bold flex items-center gap-2">
                <GraduationCap className="h-5 w-5 text-primary" /> Student Profile
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 pt-2 space-y-3 text-xs">
              <div>
                <span className="text-muted-foreground">Username:</span>{' '}
                <span className="font-semibold text-foreground">{selectedStudent.username}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Student ID:</span>{' '}
                <Badge variant="outline">{selectedStudent.id}</Badge>
              </div>
              <div>
                <span className="text-muted-foreground">Organization ID:</span>{' '}
                <Badge variant="secondary">{selectedStudent.organization_id}</Badge>
              </div>
            </CardContent>
          </Card>

          {/* Student Performance Reports List */}
          <div className="md:col-span-2 space-y-4">
            <h2 className="text-lg font-bold flex items-center gap-2">
              <FileText className="h-5 w-5 text-primary" /> Performance Reports
            </h2>

            {loading ? (
              <div className="py-12 flex justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
              </div>
            ) : studentReports.length === 0 ? (
              <Card className="border-dashed bg-muted/20">
                <CardContent className="p-8 text-center text-xs text-muted-foreground space-y-2">
                  <FileText className="h-8 w-8 mx-auto opacity-40" />
                  <p>No performance reports generated yet for this student.</p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-4">
                {studentReports.map((report) => (
                  <Card key={report.id} className="p-4 space-y-3 bg-card">
                    <div className="flex items-center justify-between border-b pb-2">
                      <span className="font-bold text-sm text-primary">{report.subject}</span>
                      <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                        <Calendar className="h-3.5 w-3.5" />
                        {new Date(report.created_at).toLocaleDateString()}
                      </div>
                    </div>
                    <div className="prose dark:prose-invert max-w-none text-xs leading-relaxed">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{report.content}</ReactMarkdown>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
