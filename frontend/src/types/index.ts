export type ReportLength = 'simple' | 'moderate' | 'detailed';
export type SearchSource = 'reddit' | 'twitter' | 'threads';
export type ScheduleStatus = 'active' | 'paused' | 'completed';

export interface User {
  id: number;
  nickname: string;
  approval_status: string;
  created_at: string;
  last_access: string;
}

export interface SearchRequest {
  query: string;
  sources: SearchSource[];
  user_nickname: string;
  session_id?: string;
  push_token?: string;
  length: ReportLength;
  schedule_yn: 'Y' | 'N';
  schedule_period?: number;
  schedule_count?: number;
  schedule_start_time?: string;
}

export interface SearchResponse {
  status: string;
  session_id: string;
  query_id: string;
  summary?: string;
  full_report?: string;
  posts_collected: number;
  estimated_time: number;
  message?: string;
  schedule_id?: number;
}

export interface Report {
  id: string;
  user_nickname: string;
  query_text: string;
  summary: string;
  full_report: string;
  posts_collected: number;
  report_length: ReportLength;
  session_id?: string;
  created_at: string;
  updated_at?: string;
}

export interface Schedule {
  id: number;
  user_nickname: string;
  keyword: string;
  interval_minutes: number;
  report_length: ReportLength;
  total_reports: number;
  completed_reports: number;
  status: ScheduleStatus;
  next_run?: string;
  last_run?: string;
  notification_enabled: boolean;
  created_at: string;
}

export interface ProgressUpdate {
  stage: string;
  message: string;
  progress: number;
  timestamp: string;
}