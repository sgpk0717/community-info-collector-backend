import axios, { AxiosInstance } from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { API_BASE_URL, STORAGE_KEYS } from '../constants/config';
import { 
  SearchRequest, 
  SearchResponse, 
  Report, 
  Schedule,
  User 
} from '../types';

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.client.interceptors.request.use(
      async (config) => {
        const token = await AsyncStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Handle unauthorized
          AsyncStorage.removeItem(STORAGE_KEYS.AUTH_TOKEN);
          AsyncStorage.removeItem(STORAGE_KEYS.USER_NICKNAME);
        }
        return Promise.reject(error);
      }
    );
  }

  // Search endpoints
  async search(request: SearchRequest): Promise<SearchResponse> {
    const response = await this.client.post<SearchResponse>('/search', request);
    return response.data;
  }

  // User endpoints
  async getOrCreateUser(nickname: string): Promise<User> {
    const response = await this.client.post<User>('/users', { nickname });
    return response.data;
  }

  async loginUser(nickname: string): Promise<{ success: boolean; user?: User; message?: string }> {
    try {
      const response = await this.client.post('/users/login', { user_nickname: nickname });
      return { success: true, user: response.data };
    } catch (error: any) {
      if (error.response?.status === 404) {
        return { success: false, message: 'User not found' };
      }
      throw error;
    }
  }

  async registerUser(nickname: string): Promise<{ success: boolean; user?: User; message?: string }> {
    try {
      const response = await this.client.post('/users/register', { user_nickname: nickname });
      return { success: true, user: response.data };
    } catch (error: any) {
      if (error.response?.status === 400) {
        return { success: false, message: error.response.data.detail || 'Registration failed' };
      }
      throw error;
    }
  }

  async checkNickname(nickname: string): Promise<{ isAvailable: boolean }> {
    try {
      const response = await this.client.get(`/users/check-nickname?nickname=${encodeURIComponent(nickname)}`);
      return { isAvailable: response.data.is_available };
    } catch (error) {
      console.error('Check nickname error:', error);
      throw error;
    }
  }

  // Report endpoints
  async getReports(userNickname: string): Promise<Report[]> {
    const response = await this.client.get<Report[]>(`/reports?user_nickname=${userNickname}`);
    return response.data;
  }

  async getReport(reportId: string): Promise<Report> {
    const response = await this.client.get<Report>(`/reports/${reportId}`);
    return response.data;
  }

  async getReportDetail(reportId: string): Promise<{ data: Report }> {
    const response = await this.client.get<Report>(`/reports/${reportId}`);
    return { data: response.data };
  }

  async getReportLinks(reportId: string): Promise<{ data: any[] }> {
    const response = await this.client.get<any[]>(`/reports/${reportId}/links`);
    return { data: response.data };
  }

  // Schedule endpoints
  async getSchedules(userNickname: string): Promise<Schedule[]> {
    const response = await this.client.get<Schedule[]>(`/schedules?user_nickname=${userNickname}`);
    return response.data;
  }

  async createSchedule(schedule: Partial<Schedule>): Promise<Schedule> {
    const response = await this.client.post<Schedule>('/schedules', schedule);
    return response.data;
  }

  async updateSchedule(scheduleId: number, updates: Partial<Schedule>): Promise<Schedule> {
    const response = await this.client.patch<Schedule>(`/schedules/${scheduleId}`, updates);
    return response.data;
  }

  async deleteSchedule(scheduleId: number): Promise<void> {
    await this.client.delete(`/schedules/${scheduleId}`);
  }
}

export const api = new ApiService();
export default api;