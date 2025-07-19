interface LogEntry {
  id: string;
  timestamp: Date;
  level: 'info' | 'warning' | 'error';
  message: string;
  details?: any;
}

class LogService {
  private logs: LogEntry[] = [];
  private maxLogs = 1000;
  private listeners: ((logs: LogEntry[]) => void)[] = [];

  info(message: string, details?: any) {
    this.addLog('info', message, details);
  }

  warning(message: string, details?: any) {
    this.addLog('warning', message, details);
  }

  error(message: string, details?: any) {
    this.addLog('error', message, details);
  }

  private addLog(level: LogEntry['level'], message: string, details?: any) {
    const entry: LogEntry = {
      id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
      timestamp: new Date(),
      level,
      message,
      details,
    };

    this.logs.unshift(entry);

    if (this.logs.length > this.maxLogs) {
      this.logs = this.logs.slice(0, this.maxLogs);
    }

    this.notifyListeners();

    // 개발 환경에서는 console에도 출력
    if (__DEV__) {
      const consoleMethod = level === 'error' ? 'error' : level === 'warning' ? 'warn' : 'log';
      console[consoleMethod](`[${level.toUpperCase()}] ${message}`, details || '');
    }
  }

  getLogs(): LogEntry[] {
    return [...this.logs];
  }

  clearLogs() {
    this.logs = [];
    this.notifyListeners();
  }

  subscribe(listener: (logs: LogEntry[]) => void): () => void {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  private notifyListeners() {
    this.listeners.forEach(listener => listener(this.getLogs()));
  }

  formatLogTime(date: Date): string {
    return date.toLocaleTimeString('ko-KR', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  }

  formatLogDate(date: Date): string {
    return date.toLocaleDateString('ko-KR', {
      month: 'short',
      day: 'numeric',
    });
  }
}

export const logService = new LogService();
export type { LogEntry };