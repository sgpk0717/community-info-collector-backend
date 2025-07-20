import { WS_BASE_URL } from '../constants/config';
import { ProgressUpdate } from '../types';

type MessageHandler = (update: ProgressUpdate) => void;
type ConnectionHandler = () => void;

class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectInterval: number = 3000;
  private shouldReconnect: boolean = true;
  private messageHandlers: Set<MessageHandler> = new Set();
  private connectionHandlers: Set<ConnectionHandler> = new Set();
  private disconnectionHandlers: Set<ConnectionHandler> = new Set();
  private sessionId: string | null = null;

  connect(sessionId: string) {
    this.sessionId = sessionId;
    this.shouldReconnect = true;
    this.createConnection();
  }

  private createConnection() {
    if (!this.sessionId) return;

    try {
      this.ws = new WebSocket(`${WS_BASE_URL}/${this.sessionId}`);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.connectionHandlers.forEach(handler => handler());
      };

      this.ws.onmessage = (event) => {
        try {
          const update: ProgressUpdate = JSON.parse(event.data);
          this.messageHandlers.forEach(handler => handler(update));
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        this.disconnectionHandlers.forEach(handler => handler());
        
        if (this.shouldReconnect) {
          setTimeout(() => {
            console.log('Attempting to reconnect WebSocket...');
            this.createConnection();
          }, this.reconnectInterval);
        }
      };
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
    }
  }

  disconnect() {
    this.shouldReconnect = false;
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.sessionId = null;
  }

  onMessage(handler: MessageHandler) {
    this.messageHandlers.add(handler);
    return () => {
      this.messageHandlers.delete(handler);
    };
  }

  onConnect(handler: ConnectionHandler) {
    this.connectionHandlers.add(handler);
    return () => {
      this.connectionHandlers.delete(handler);
    };
  }

  onDisconnect(handler: ConnectionHandler) {
    this.disconnectionHandlers.add(handler);
    return () => {
      this.disconnectionHandlers.delete(handler);
    };
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

export default new WebSocketService();