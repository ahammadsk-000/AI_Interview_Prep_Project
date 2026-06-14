// API contract types mirroring the FastAPI backend DTOs.

export interface UserPublic {
  id: string;
  email: string;
  full_name: string | null;
  avatar_url: string | null;
  target_role: string | null;
  experience_level: string | null;
  is_active: boolean;
  is_verified: boolean;
  roles: string[];
  plan: string | null;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface AuthResponse {
  user: UserPublic;
  tokens: TokenPair;
}

export interface CodingStats {
  submissions: number;
  accepted: number;
  acceptance_rate: number;
  avg_readiness: number;
  best_readiness: number;
}

export interface AtsStats {
  reports: number;
  latest_score: number | null;
  best_score: number | null;
  improvement_delta: number;
}

export interface InterviewStats {
  total: number;
  completed: number;
  avg_score: number | null;
}

export interface DashboardOverview {
  totals: Record<string, number>;
  overall_readiness: number | null;
  dimension_averages: Record<string, number>;
  coding: CodingStats;
  ats: AtsStats;
  interviews: InterviewStats;
}

export interface TrendPoint {
  period: string;
  value: number;
  count: number;
}

export interface TrendResponse {
  metric: string;
  bucket: string;
  points: TrendPoint[];
  summary: {
    count: number;
    average: number;
    minimum: number;
    maximum: number;
    delta: number;
    direction: string;
  };
}

export interface ResumePublic {
  id: string;
  filename: string;
  mime: string;
  status: string;
  parsed_chars: number;
  created_at: string;
}

export interface SessionState {
  interview_id: string;
  session_id: string;
  type: string;
  status: string;
  current_difficulty: string;
  planned_questions: number;
  questions_asked: number;
  current_question: string | null;
  done: boolean;
  summary: string | null;
  avg_score: number | null;
}

export interface AnswerGrade {
  score_id: string | null;
  total: number;
  score_out_of_10: number;
  dimensions: Record<string, number>;
  feedback: string[];
  suggested_better_answer: string;
  industry_standard_answer: string;
}

export interface ChallengeSummary {
  id: string;
  slug: string;
  title: string;
  difficulty: string;
  tags: string[];
}

export interface SubmissionResult {
  submission_id: string | null;
  status: string;
  passed: number;
  total: number;
  correctness_score: number;
  edge_case_score: number;
  code_quality_score: number;
  time_complexity: string;
  space_complexity: string;
  readiness_score: number;
  difficulty_rating: string;
  runtime_ms: number | null;
  suggestions: string[];
  cases: { index: number; passed: boolean; is_hidden: boolean; error: string | null }[];
}

export interface VisibleTestCase {
  args: unknown[];
  expected: unknown;
}

export interface ChallengeDetail {
  id: string;
  slug: string;
  title: string;
  difficulty: string;
  prompt: string;
  entrypoint: string;
  starter_code: Record<string, string>;
  tags: string[];
  is_public: boolean;
  visible_test_cases: VisibleTestCase[];
  hidden_test_count: number;
}

export interface AtsReport {
  id: string;
  resume_id: string;
  ats_score: number;
  recruiter_score: number;
  tech_score: number;
  comm_score: number;
  readiness: number;
  matched_keywords: string[];
  missing_keywords: string[];
  suggestions: string[];
  created_at: string;
}

export interface OptimizeResponse {
  ats_compatibility: number;
  missing_keywords: string[];
  recruiter_insights: string[];
  improved_resume_text: string;
  report: AtsReport;
}

export interface AgentStep {
  agent: string;
  status: string;
  summary: string;
  latency_ms: number;
}

export interface AgentRun {
  id: string;
  graph: string;
  status: string;
  trace_id: string;
  output: Record<string, unknown>;
  steps: AgentStep[];
  tokens: number;
  created_at: string;
}

export interface OrgPublic {
  id: string;
  name: string;
  slug: string;
  plan: string;
  your_role: string;
  member_count: number;
}

export interface MemberPublic {
  user_id: string;
  email: string;
  full_name: string | null;
  role: string;
}

export interface MemberReadiness {
  user_id: string;
  email: string;
  role: string;
  overall_readiness: number | null;
  interviews: number;
  coding_submissions: number;
}

export interface MentorDashboard {
  organization_id: string;
  member_count: number;
  average_readiness: number | null;
  members: MemberReadiness[];
}

export interface HistoryItem {
  kind: string;
  label: string;
  score: number | null;
  status: string | null;
  occurred_at: string;
}

export interface VoiceSession {
  id: string;
  interview_session_id: string;
  status: string;
  created_at: string;
}

export interface VoiceTurnResponse {
  transcript: string;
  confidence: number;
  next_question: string | null;
  done: boolean;
  question_audio_b64: string | null;
  summary: string | null;
}

export interface ApiError {
  error: { code: string; message: string };
}
