import type {
  AnalyticsOverview,
  DashboardSummary,
  EmailListResponse,
  EmailScanDetail,
  ModelInfo,
  ScannerStatus,
  UserProfile,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

class ApiService {
  private getToken(): string | null {
    return localStorage.getItem('zander_auth_token');
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      // Clear token and redirect to login if session expired
      localStorage.removeItem('zander_auth_token');
      localStorage.removeItem('zander_user');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
      throw new Error('Authentication required');
    }

    if (!response.ok) {
      let errorMessage = `HTTP ${response.status} Error`;
      try {
        const errorJson = await response.json();
        if (errorJson.detail) {
          errorMessage = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail);
        }
      } catch {
        // Fallback to status text
      }
      throw new Error(errorMessage);
    }

    return response.json();
  }

  async login(username: string, password: string): Promise<{ access_token: string; username: string }> {
    return this.request<{ access_token: string; username: string }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
  }

  async getProfile(): Promise<UserProfile> {
    return this.request<UserProfile>('/api/auth/me');
  }

  async getDashboardSummary(): Promise<DashboardSummary> {
    return this.request<DashboardSummary>('/api/dashboard/summary');
  }

  async getEmails(params: {
    page?: number;
    pageSize?: number;
    search?: string;
    classification?: string;
    sortBy?: string;
    sortOrder?: 'asc' | 'desc';
  } = {}): Promise<EmailListResponse> {
    const query = new URLSearchParams();
    if (params.page) query.append('page', params.page.toString());
    if (params.pageSize) query.append('page_size', params.pageSize.toString());
    if (params.search) query.append('search', params.search);
    if (params.classification && params.classification !== 'ALL') {
      query.append('classification', params.classification);
    }
    if (params.sortBy) query.append('sort_by', params.sortBy);
    if (params.sortOrder) query.append('sort_order', params.sortOrder);

    return this.request<EmailListResponse>(`/api/emails?${query.toString()}`);
  }

  async getEmailDetail(id: number): Promise<EmailScanDetail> {
    return this.request<EmailScanDetail>(`/api/emails/${id}`);
  }

  async fetchEmailBody(id: number): Promise<EmailScanDetail> {
    return this.request<EmailScanDetail>(`/api/emails/${id}/fetch-body`, {
      method: 'POST',
    });
  }

  async getAnalytics(startDate?: string, endDate?: string): Promise<AnalyticsOverview> {
    const query = new URLSearchParams();
    if (startDate) query.append('start_date', startDate);
    if (endDate) query.append('end_date', endDate);
    const queryString = query.toString();
    return this.request<AnalyticsOverview>(`/api/analytics/overview${queryString ? `?${queryString}` : ''}`);
  }

  async getScannerStatus(): Promise<ScannerStatus> {
    return this.request<ScannerStatus>('/api/monitor/status');
  }

  async getModelInfo(): Promise<ModelInfo> {
    return this.request<ModelInfo>('/api/model/info');
  }

  async getHealth(): Promise<{ status: string; database_connected: boolean; timestamp: string }> {
    return this.request<{ status: string; database_connected: boolean; timestamp: string }>('/api/health');
  }
}

export const api = new ApiService();
