export const API_BASE_URL = __DEV__ 
  ? 'http://10.0.2.2:8000/api/v1'  // Android emulator
  : 'https://community-info-collector-backend.onrender.com/api/v1';

export const WS_BASE_URL = __DEV__
  ? 'ws://10.0.2.2:8000/ws'
  : 'wss://community-info-collector-backend.onrender.com/ws';

export const APP_CONFIG = {
  appName: 'Community Info Collector',
  version: '2.0.0',
  defaultLanguage: 'ko',
  
  // API 타임아웃 설정
  apiTimeout: 30000,
  wsReconnectInterval: 3000,
  
  // 보고서 설정
  reportLengthOptions: [
    { value: 'simple', label: '간단히' },
    { value: 'moderate', label: '보통' },
    { value: 'detailed', label: '상세히' },
  ],
  
  // 스케줄 옵션
  scheduleOptions: [
    { value: 60, label: '매시간' },
    { value: 720, label: '12시간마다' },
    { value: 1440, label: '매일' },
    { value: 10080, label: '매주' },
  ],
};

export const STORAGE_KEYS = {
  USER_NICKNAME: '@user_nickname',
  SAVED_NICKNAME: '@saved_nickname',
  AUTH_TOKEN: '@auth_token',
  RECENT_SEARCHES: '@recent_searches',
  THEME: '@theme',
};