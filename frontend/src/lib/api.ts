/**
 * API Client for Requirements Support AI System
 */

import axios, { AxiosInstance } from "axios";

// ========== Types ==========

export type QuestionCategory = "functional" | "non_functional" | "constraint" | "other";
export type QuestionPriority = "high" | "medium" | "low";
export type IssueSeverity = "high" | "medium" | "low";
export type IssueCategory = "missing" | "inconsistency" | "ambiguity" | "quality";

export interface Question {
  id: string;
  category: QuestionCategory;
  question: string;
  priority: QuestionPriority;
  context?: string;
}

export interface BreakdownInitializeRequest {
  input_text: string;
  session_id?: string;
}

export interface BreakdownInitializeResponse {
  session_id: string;
  draft_requirements: string;
  questions: Question[];
  completion_rate: number;
  answered_count: number;
  total_count: number;
  system_message?: string;
}

export interface BreakdownAnswerRequest {
  session_id: string;
  question_id: string;
  answer: string;
}

export interface BreakdownAnswerResponse {
  updated_requirements: string;
  new_questions: Question[];
  completion_rate: number;
  all_answered: boolean;
  answered_count: number;
  total_count: number;
  follow_up_question: string | null;
  answer_accepted: boolean;
  system_message?: string;
  update_summary?: string;
  next_questions_message?: string;
}

export interface BreakdownStatusResponse {
  session_id: string;
  requirements: string;
  answered_questions: Question[];
  remaining_questions: Question[];
  completion_rate: number;
}

export interface ReviewRequest {
  requirements_text: string;
}

export interface ReviewIssue {
  severity: IssueSeverity;
  category: IssueCategory;
  section: string;
  line?: number;
  description: string;
  suggestion: string;
}

export interface ReviewResponse {
  review_id: string;
  issues: ReviewIssue[];
  completeness_score: number;
  consistency_score: number;
  quality_score: number;
  summary: string;
}

// ========== API Client ==========

/**
 * Determine the API base URL at runtime for browser compatibility
 * This supports:
 * 1. Explicit backend URL from environment (NEXT_PUBLIC_BACKEND_URL)
 * 2. Same-host access (when frontend and backend are on the same server)
 * 3. Remote access (when accessing from different network)
 */
function getAPIBaseURL(): string {
  // If NEXT_PUBLIC_BACKEND_URL is set, use it (for remote access scenarios)
  if (process.env.NEXT_PUBLIC_BACKEND_URL) {
    return process.env.NEXT_PUBLIC_BACKEND_URL;
  }

  // For browser environment, detect the current host and use port 8010
  if (typeof window !== "undefined") {
    const protocol = window.location.protocol;
    const hostname = window.location.hostname;
    // Assume backend is on port 8010 (configurable via NEXT_PUBLIC_BACKEND_URL if different)
    return `${protocol}//${hostname}:8010`;
  }

  // Fallback for SSR or build-time (should not be used in production)
  return "http://localhost:8010";
}

class APIClient {
  private client: AxiosInstance;

  constructor() {
    const baseURL = getAPIBaseURL();
    this.client = axios.create({
      baseURL,
      headers: {
        "Content-Type": "application/json",
      },
      timeout: 120000, // 2 minutes for LLM operations
    });
  }

  // ========== Breakdown API ==========

  async initializeBreakdown(
    data: BreakdownInitializeRequest
  ): Promise<BreakdownInitializeResponse> {
    const response = await this.client.post<BreakdownInitializeResponse>(
      "/api/breakdown/initialize",
      data
    );
    return response.data;
  }

  async answerQuestion(
    data: BreakdownAnswerRequest
  ): Promise<BreakdownAnswerResponse> {
    const response = await this.client.post<BreakdownAnswerResponse>(
      "/api/breakdown/answer",
      data
    );
    return response.data;
  }

  async getBreakdownStatus(
    sessionId: string
  ): Promise<BreakdownStatusResponse> {
    const response = await this.client.get<BreakdownStatusResponse>(
      `/api/breakdown/status/${sessionId}`
    );
    return response.data;
  }

  // ========== Review API ==========

  async reviewRequirements(data: ReviewRequest): Promise<ReviewResponse> {
    const response = await this.client.post<ReviewResponse>(
      "/api/review",
      data
    );
    return response.data;
  }

  // ========== Health Check ==========

  async healthCheck(): Promise<{ status: string }> {
    const response = await this.client.get<{ status: string }>("/health");
    return response.data;
  }
}

// Export singleton instance
export const apiClient = new APIClient();
