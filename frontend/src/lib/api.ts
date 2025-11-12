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

class APIClient {
  private client: AxiosInstance;

  constructor() {
    const baseURL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
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
