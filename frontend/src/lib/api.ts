const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private getToken(): string | null {
    return localStorage.getItem("access_token");
  }

  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      window.location.href = "/login";
      throw new Error("Unauthorized");
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Request failed" }));
      throw new Error(error.detail || "Request failed");
    }

    return response.json();
  }

  async get<T>(path: string): Promise<T> {
    return this.request<T>(path);
  }

  async post<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>(path, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  async put<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>(path, {
      method: "PUT",
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  async delete<T>(path: string): Promise<T> {
    return this.request<T>(path, { method: "DELETE" });
  }

  async uploadFile<T>(path: string, file: File, params?: Record<string, string>): Promise<T> {
    const token = this.getToken();
    const formData = new FormData();
    formData.append("file", file);

    const queryStr = params ? "?" + new URLSearchParams(params).toString() : "";

    const response = await fetch(`${this.baseUrl}${path}${queryStr}`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Upload failed" }));
      throw new Error(error.detail || "Upload failed");
    }

    return response.json();
  }

  // Auth
  async register(data: { email: string; password: string; full_name: string; display_name?: string; date_of_birth?: string }) {
    return this.post<{ access_token: string; refresh_token: string }>("/api/v1/auth/register", data);
  }

  async login(data: { email: string; password: string }) {
    return this.post<{ access_token: string; refresh_token: string }>("/api/v1/auth/login", data);
  }

  async getMe() {
    return this.get<UserProfile>("/api/v1/auth/me");
  }

  async verifyEmail(token: string) {
    return this.post<{ message: string }>("/api/v1/auth/verify-email", { token });
  }

  async forgotPassword(email: string) {
    return this.post<{ message: string }>("/api/v1/auth/forgot-password", { email });
  }

  async resetPassword(token: string, new_password: string) {
    return this.post<{ message: string }>("/api/v1/auth/reset-password", { token, new_password });
  }

  // Score
  async getScore() {
    return this.get<ScoreData>("/api/v1/score");
  }

  async getScoreHistory() {
    return this.get<{ history: ScoreHistoryItem[] }>("/api/v1/score/history");
  }

  async startAudit() {
    return this.post<{ message: string; audit_id: string; status: string }>("/api/v1/audit/start");
  }

  async getAuditStatus() {
    return this.get<AuditStatus>("/api/v1/audit/status");
  }

  // Findings
  async getFindings(params?: { source?: string; category?: string; severity?: string; page?: number; page_size?: number }) {
    const query = params ? "?" + new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)])
    ).toString() : "";
    return this.get<FindingsResponse>(`/api/v1/findings${query}`);
  }

  async getFinding(id: string) {
    return this.get<Finding>(`/api/v1/findings/${id}`);
  }

  // Disputes
  async createDispute(findingId: string, data: { reason: string; supporting_evidence?: string }) {
    return this.post<Dispute>(`/api/v1/findings/${findingId}/dispute`, data);
  }

  async getDisputes() {
    return this.get<{ disputes: Dispute[]; total: number }>("/api/v1/disputes");
  }

  // Accounts
  async getAccounts() {
    return this.get<{ accounts: SocialAccount[] }>("/api/v1/accounts");
  }

  async connectTwitter() {
    return this.post<SocialAccount>("/api/v1/accounts/connect/twitter");
  }

  async uploadArchive(platform: string, file: File) {
    return this.uploadFile<{ message: string }>("/api/v1/accounts/upload", file, { platform });
  }

  async disconnectAccount(id: string) {
    return this.delete<{ message: string }>(`/api/v1/accounts/${id}`);
  }

  // Public
  async searchPublic(query: string) {
    return this.get<PublicSearchResponse>(`/api/v1/public/search?q=${encodeURIComponent(query)}`);
  }

  async getPublicProfile(username: string) {
    return this.get<PublicProfile>(`/api/v1/public/profile/${username}`);
  }

  async claimProfile(profileId: string) {
    return this.post<{ message: string }>("/api/v1/public/claim", { profile_id: profileId });
  }

  async getScorecard(userId: string) {
    return this.get<Scorecard>(`/api/v1/public/scorecard/${userId}`);
  }

  // Payments
  async createCheckout(priceType: "audit" | "subscriber" | "employer") {
    return this.post<{ checkout_url: string; session_id: string }>("/api/v1/payments/checkout", { price_type: priceType });
  }

  async getSubscription() {
    return this.get<{ tier: string; status: string; stripe_customer_id: string | null }>("/api/v1/payments/subscription");
  }

  // Employer
  async employerSearch(name: string, username?: string) {
    return this.post<EmployerReport>("/api/v1/employer/search", { name, username });
  }
}

// Types
export interface UserProfile {
  id: string;
  email: string;
  full_name: string | null;
  display_name: string | null;
  date_of_birth: string | null;
  email_verified: boolean;
  subscription_tier: string;
  subscription_status: string;
  is_profile_claimed: boolean;
  profile_visibility: string;
}

export interface ScoreData {
  overall_score: number;
  social_media_score: number;
  web_presence_score: number;
  posting_behavior_score: number;
  score_accuracy_pct: number;
  is_verified: boolean;
  verification_date: string | null;
  score_breakdown: {
    components: Record<string, { score: number; weight: number; impact: number }>;
    categories: Record<string, { count: number; total_impact: number; severity: string }>;
    juvenile_exclusions: number;
    disputed_exclusions: number;
  };
  calculated_at: string;
  score_color: string;
  score_label: string;
}

export interface ScoreHistoryItem {
  overall_score: number;
  social_media_score: number;
  web_presence_score: number;
  posting_behavior_score: number;
  recorded_at: string;
}

export interface AuditStatus {
  status: string;
  progress_pct: number;
  platforms_scanned: string[];
  findings_count: number;
  message: string;
}

export interface Finding {
  id: string;
  source: string;
  source_type: string;
  category: string;
  severity: string;
  title: string;
  description: string | null;
  evidence_snippet: string | null;
  evidence_url: string | null;
  original_date: string | null;
  platform_engagement_count: number;
  is_disputed: boolean;
  dispute_status: string | null;
  is_juvenile_content: boolean;
  base_score_impact: number;
  final_score_impact: number;
  created_at: string;
}

export interface FindingsResponse {
  findings: Finding[];
  total: number;
  page: number;
  page_size: number;
}

export interface Dispute {
  id: string;
  finding_id: string;
  reason: string;
  supporting_evidence: string | null;
  status: string;
  reviewer_notes: string | null;
  submitted_at: string;
  resolved_at: string | null;
}

export interface SocialAccount {
  id: string;
  platform: string;
  platform_username: string | null;
  connection_type: string;
  last_scan_at: string | null;
  created_at: string;
}

export interface PublicProfile {
  id: string;
  lookup_name: string;
  lookup_username: string | null;
  public_score: number | null;
  score_accuracy_pct: number | null;
  is_claimed: boolean;
  score_color: string | null;
  score_label: string | null;
  last_scanned_at: string | null;
  public_findings_summary: Record<string, unknown> | null;
}

export interface PublicSearchResponse {
  results: PublicProfile[];
  total: number;
}

export interface Scorecard {
  user_id: string;
  display_name: string;
  overall_score: number;
  social_media_score: number;
  web_presence_score: number;
  posting_behavior_score: number;
  score_accuracy_pct: number;
  is_verified: boolean;
  score_color: string;
  score_label: string;
  calculated_at: string;
  share_url: string;
  platforms_analyzed: string[];
  total_findings: number;
  category_breakdown: Record<string, number>;
}

export interface EmployerReport {
  results: PublicProfile[];
  total: number;
  profile: PublicProfile;
  findings_summary: Record<string, number>;
  risk_level: string;
  recommendation: string;
  searched_at: string;
}

export const api = new ApiClient(API_URL);
