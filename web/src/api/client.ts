// Centralized API client service for connecting to FastAPI backend

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

export interface User {
  id: number
  username: string
  role: 'student' | 'teacher'
  organization_id: number
}

export interface Organization {
  id: number
  name: string
}

export interface SessionSummary {
  id: string
  session_id?: string
  title: string
  subject: string
  topics: string[]
  created_at?: string
  last_updated?: string
}

export interface SubjectItem {
  id: number
  name: string
  topics: string[]
}

export interface ChatMessage {
  role: 'user' | 'model' | 'assistant' | 'teacher'
  content: string
  author?: string
  visible_to_student?: boolean
  timestamp?: string
  selected_text?: string
}

export interface TextbookArticle {
  session_id: string
  title: string
  topics: string[]
  markdown_content: string
  generated_at?: string
}

export interface ReportItem {
  id: number
  session_id?: string
  student_id: number
  subject: string
  content: string
  created_at: string
}

export interface ReviewSheet {
  summary: string
  key_points: string[]
  action_items: string[]
  compiled_at: string
}

export interface LearningModule {
  title: string
  description: string
  topics: string[]
}

export interface LearningPlan {
  modules: LearningModule[]
}

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

function getAuthHeader(): Record<string, string> {
  const token = localStorage.getItem('access_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorDetail = 'An unexpected error occurred'
    try {
      const errorData = await response.json()
      if (typeof errorData.detail === 'string') {
        errorDetail = errorData.detail
      } else if (Array.isArray(errorData.detail)) {
        errorDetail = errorData.detail.map((e: any) => e.msg || JSON.stringify(e)).join(', ')
      } else if (errorData.detail) {
        errorDetail = typeof errorData.detail === 'object' ? JSON.stringify(errorData.detail) : String(errorData.detail)
      }
    } catch {
      // ignore json parse error
    }
    if (response.status === 401 && typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('socratic:unauthorized', { detail: { message: errorDetail } }))
    }
    throw new ApiError(errorDetail, response.status)
  }
  return response.json() as Promise<T>
}

export const api = {
  // Auth API
  async getOrganizations(): Promise<Organization[]> {
    const res = await fetch(`${BASE_URL}/auth/organizations`)
    return handleResponse<Organization[]>(res)
  },

  async register(data: {
    username: string
    password: string
    role: 'student' | 'teacher'
    organization_id?: number
    new_organization_name?: string
  }): Promise<User> {
    const res = await fetch(`${BASE_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse<User>(res)
  },

  async login(username: string, password: string): Promise<{ access_token: string; token_type: string }> {
    const formData = new URLSearchParams()
    formData.append('username', username)
    formData.append('password', password)

    const res = await fetch(`${BASE_URL}/auth/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData,
    })
    const tokenResponse = await handleResponse<{ access_token: string; token_type: string }>(res)
    localStorage.setItem('access_token', tokenResponse.access_token)
    return tokenResponse
  },

  logout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_info')
  },

  // Chat & Socratic Sessions
  async getSessions(): Promise<SessionSummary[]> {
    const res = await fetch(`${BASE_URL}/chat/sessions`, {
      headers: getAuthHeader(),
    })
    const rawSessions = await handleResponse<any[]>(res)
    return rawSessions.map((s) => ({
      id: s.id || s.session_id,
      session_id: s.session_id || s.id,
      title: s.title || (s.topics?.length ? `${s.subject} - ${s.topics.join(', ')}` : `${s.subject || 'General'}`),
      subject: s.subject || 'General',
      topics: s.topics || [],
      created_at: s.created_at,
      last_updated: s.last_updated,
    }))
  },

  async getSubjects(): Promise<SubjectItem[]> {
    const res = await fetch(`${BASE_URL}/chat/subjects`, {
      headers: getAuthHeader(),
    })
    return handleResponse<SubjectItem[]>(res)
  },

  async validateSubject(name: string): Promise<SubjectItem> {
    const res = await fetch(`${BASE_URL}/chat/subjects/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      body: JSON.stringify({ name, topics: [] }),
    })
    return handleResponse<SubjectItem>(res)
  },

  async startSession(subject: string, topics: string[]): Promise<{ session_id: string }> {
    const res = await fetch(`${BASE_URL}/chat/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      body: JSON.stringify({ subject, topics }),
    })
    return handleResponse<{ session_id: string }>(res)
  },

  async sendMessage(sessionId: string, prompt: string): Promise<{ response: string }> {
    const res = await fetch(`${BASE_URL}/chat/${sessionId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      body: JSON.stringify({ prompt }),
    })
    return handleResponse<{ response: string }>(res)
  },

  async getHistory(sessionId: string): Promise<{
    messages: ChatMessage[]
    learning_plan?: any
    subject: string
    topics?: string[]
    title?: string
    highlights?: Array<{
      element_id?: string
      quoted_text: string
      question?: string
      tag?: string
      created_at?: string
    }>
  }> {
    const res = await fetch(`${BASE_URL}/chat/${sessionId}/history`, {
      headers: getAuthHeader(),
    })
    return handleResponse<{
      messages: ChatMessage[]
      learning_plan?: any
      subject: string
      topics?: string[]
      title?: string
      highlights?: Array<{
        element_id?: string
        quoted_text: string
        question?: string
        tag?: string
        created_at?: string
      }>
    }>(res)
  },

  async addHighlight(
    sessionId: string,
    highlight: { element_id?: string; quoted_text: string; question?: string; tag?: string }
  ): Promise<any> {
    const res = await fetch(`${BASE_URL}/chat/${sessionId}/highlight`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      body: JSON.stringify(highlight),
    })
    return handleResponse<any>(res)
  },

  async getHighlights(sessionId: string): Promise<any[]> {
    const res = await fetch(`${BASE_URL}/chat/${sessionId}/highlights`, {
      headers: getAuthHeader(),
    })
    return handleResponse<any[]>(res)
  },

  async deleteHighlight(sessionId: string, index: number): Promise<any> {
    const res = await fetch(`${BASE_URL}/chat/${sessionId}/highlight/${index}`, {
      method: 'DELETE',
      headers: getAuthHeader(),
    })
    return handleResponse<any>(res)
  },

  async getLearningPlan(sessionId: string): Promise<LearningPlan> {
    const res = await fetch(`${BASE_URL}/chat/learning/plan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      body: JSON.stringify({ session_id: sessionId }),
    })
    return handleResponse<LearningPlan>(res)
  },

  async generateTextbook(sessionId: string, topicOverride?: string): Promise<TextbookArticle> {
    const res = await fetch(`${BASE_URL}/chat/textbook/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      body: JSON.stringify({ session_id: sessionId, topic_override: topicOverride }),
    })
    return handleResponse<TextbookArticle>(res)
  },

  async getSocraticHint(sessionId: string, question: string, articleText?: string): Promise<{ hint: string; excerpt?: string }> {
    const res = await fetch(`${BASE_URL}/chat/textbook/socratic-hint`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      body: JSON.stringify({ session_id: sessionId, question, article_text: articleText }),
    })
    return handleResponse<{ hint: string; excerpt?: string }>(res)
  },

  async generateQuiz(sessionId: string, difficulty: 'easy' | 'mid' | 'hard'): Promise<any> {
    const res = await fetch(`${BASE_URL}/chat/quiz/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      body: JSON.stringify({ session_id: sessionId, difficulty }),
    })
    return handleResponse<any>(res)
  },

  async submitQuiz(quizId: number | string, userAnswers: Record<string, number>): Promise<any> {
    const res = await fetch(`${BASE_URL}/chat/quiz/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      body: JSON.stringify({ quiz_id: quizId, user_answers: userAnswers }),
    })
    return handleResponse<any>(res)
  },

  // Reports & Batch Review Summaries
  async getStudents(): Promise<User[]> {
    const res = await fetch(`${BASE_URL}/reports/students`, {
      headers: getAuthHeader(),
    })
    return handleResponse<User[]>(res)
  },

  async getStudentReports(studentId: number): Promise<ReportItem[]> {
    const res = await fetch(`${BASE_URL}/reports/student/${studentId}`, {
      headers: getAuthHeader(),
    })
    return handleResponse<ReportItem[]>(res)
  },

  async generateReport(studentId: number, sessionId: string, subject?: string): Promise<ReportItem> {
    const res = await fetch(`${BASE_URL}/reports/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      body: JSON.stringify({ student_id: studentId, session_id: sessionId, subject }),
    })
    return handleResponse<ReportItem>(res)
  },

  async compileReviewSheet(
    sessionId: string,
    highlights: Array<{ text: string; note?: string; section?: string }>,
    studentId?: number
  ): Promise<ReviewSheet> {
    const res = await fetch(`${BASE_URL}/reports/review-sheet`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      body: JSON.stringify({ session_id: sessionId, student_id: studentId, highlights }),
    })
    return handleResponse<ReviewSheet>(res)
  },

  async generateCertificate(sessionId: string, subject?: string): Promise<{ content: string; verification_hash: string; created_at: string }> {
    const res = await fetch(`${BASE_URL}/reports/certificate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      body: JSON.stringify({ session_id: sessionId, subject }),
    })
    return handleResponse<{ content: string; verification_hash: string; created_at: string }>(res)
  },
}
