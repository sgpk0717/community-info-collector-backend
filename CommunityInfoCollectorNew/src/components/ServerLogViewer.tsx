import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  Modal,
  SafeAreaView,
  ActivityIndicator,
  RefreshControl,
  Dimensions,
  Platform,
} from 'react-native';

const API_BASE_URL = 'https://community-info-collector-backend.onrender.com';
const LINES_PER_LOAD = 100;

interface ServerLogViewerProps {
  visible: boolean;
  onClose: () => void;
}

const ServerLogViewer: React.FC<ServerLogViewerProps> = ({ visible, onClose }) => {
  const [logs, setLogs] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [offset, setOffset] = useState(0);
  const [totalLines, setTotalLines] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [loadedLines, setLoadedLines] = useState(0);
  const [isAtBottom, setIsAtBottom] = useState(false);
  const scrollViewRef = useRef<ScrollView>(null);
  const [contentHeight, setContentHeight] = useState(0);
  const [scrollViewHeight, setScrollViewHeight] = useState(0);

  const fetchLogs = async (currentOffset: number, append: boolean = false, isRefresh: boolean = false, fetchLatest: boolean = false) => {
    if (fetchLatest) {
      setIsRefreshing(true);
    } else if (isRefresh) {
      setIsRefreshing(true);
    } else if (append) {
      setIsLoadingMore(true);
    } else {
      setIsLoading(true);
    }

    try {
      let response;
      
      if (fetchLatest) {
        // 최신 로그 100줄 가져오기
        response = await fetch(
          `${API_BASE_URL}/api/v1/logs/tail?lines=${LINES_PER_LOAD}&offset=0`
        );
      } else {
        // 기존 로직
        const linesToLoad = isRefresh ? loadedLines + LINES_PER_LOAD : LINES_PER_LOAD;
        response = await fetch(
          `${API_BASE_URL}/api/v1/logs/tail?lines=${linesToLoad}&offset=${currentOffset}`
        );
      }
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (fetchLatest) {
        // 최신 로그로 교체
        setLogs(data.content);
        setOffset(0);
        setLoadedLines(data.content.length);
      } else if (append) {
        setLogs(prev => [...data.content, ...prev]);
        setLoadedLines(loadedLines + data.content.length);
      } else {
        setLogs(data.content);
        setLoadedLines(isRefresh ? data.content.length : data.content.length);
      }
      
      setTotalLines(data.total_lines);
      setHasMore(currentOffset + LINES_PER_LOAD < data.total_lines);
      
    } catch (error) {
      console.error('로그 가져오기 실패:', error);
    } finally {
      setIsLoading(false);
      setIsLoadingMore(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    if (visible) {
      setOffset(0);
      setLoadedLines(0);
      fetchLogs(0);
    }
  }, [visible]);

  const handleRefresh = () => {
    // 리프레시 시 offset은 0으로 유지하고 더 많은 로그를 로드
    fetchLogs(0, false, true);
  };

  const handleLoadMore = () => {
    if (!isLoadingMore && hasMore) {
      const newOffset = offset + LINES_PER_LOAD;
      setOffset(newOffset);
      fetchLogs(newOffset, true);
    }
  };

  const handleScroll = (event: any) => {
    const { contentOffset, contentSize, layoutMeasurement } = event.nativeEvent;
    
    // 스크롤 위치 계산
    const currentScrollPosition = contentOffset.y;
    const contentH = contentSize.height;
    const scrollViewH = layoutMeasurement.height;
    
    // 맨 아래 여부 확인 (하단에서 50픽셀 이내)
    const isNearBottom = currentScrollPosition + scrollViewH >= contentH - 50;
    setIsAtBottom(isNearBottom);
    
    // 맨 위로 스크롤했을 때 더 많은 로그 로드
    if (contentOffset.y <= 0 && !isLoadingMore && hasMore) {
      handleLoadMore();
    }
  };
  
  const handleFetchLatest = () => {
    // 최신 로그 가져오기
    fetchLogs(0, false, false, true);
  };

  const removeAnsiCodes = (text: string): string => {
    // ANSI 컬러 코드 제거
    return text.replace(/\u001b\[[0-9;]*m/g, '');
  };

  const getLogColor = (line: string): string => {
    const cleanLine = removeAnsiCodes(line);
    if (cleanLine.includes('ERROR') || cleanLine.includes('에러')) {
      return '#FF3B30';
    } else if (cleanLine.includes('WARNING') || cleanLine.includes('경고')) {
      return '#FF9500';
    } else if (cleanLine.includes('INFO')) {
      return '#4A90E2';
    } else if (cleanLine.includes('DEBUG')) {
      return '#666';
    }
    return '#FFFFFF';
  };

  return (
    <Modal
      visible={visible}
      animationType="slide"
      onRequestClose={onClose}
    >
      <SafeAreaView style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.title}>서버 로그</Text>
          <TouchableOpacity onPress={onClose} style={styles.closeButton}>
            <Text style={styles.closeButtonText}>닫기</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.info}>
          <View style={styles.infoLeft}>
            <Text style={styles.infoText}>
              전체 {totalLines}줄 | 로드됨: {loadedLines}줄 | 표시: {logs.length}줄
            </Text>
            {hasMore && (
              <Text style={styles.infoText}>
                위로 스크롤하거나 아래로 당겨서 더 보기
              </Text>
            )}
          </View>
          {!isAtBottom && (
            <TouchableOpacity onPress={handleFetchLatest} style={styles.latestButton}>
              <Text style={styles.latestButtonText}>최신 로그</Text>
            </TouchableOpacity>
          )}
        </View>

        {isLoading ? (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color="#4A90E2" />
            <Text style={styles.loadingText}>로그 불러오는 중...</Text>
          </View>
        ) : (
          <ScrollView
            ref={scrollViewRef}
            style={styles.scrollView}
            contentContainerStyle={styles.scrollContent}
            onScroll={handleScroll}
            scrollEventThrottle={16}
            refreshControl={
              <RefreshControl
                refreshing={isRefreshing}
                onRefresh={handleRefresh}
                tintColor="#4A90E2"
                title={isRefreshing ? "로그 불러오는 중..." : "아래로 당겨서 더 보기"}
                titleColor="#666"
              />
            }
          >
            {isLoadingMore && (
              <View style={styles.loadingMoreContainer}>
                <ActivityIndicator size="small" color="#4A90E2" />
                <Text style={styles.loadingMoreText}>이전 로그 불러오는 중...</Text>
              </View>
            )}
            
            {logs.map((line, index) => {
              const cleanLine = removeAnsiCodes(line);
              const color = getLogColor(line);
              
              return (
                <View key={`${offset}-${index}`} style={styles.logLine}>
                  <Text style={[styles.logText, { color }]}>
                    {cleanLine}
                  </Text>
                </View>
              );
            })}
          </ScrollView>
        )}
      </SafeAreaView>
    </Modal>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
  title: {
    fontSize: 18,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  closeButton: {
    padding: 8,
  },
  closeButtonText: {
    fontSize: 16,
    color: '#4A90E2',
  },
  info: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: '#111',
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
  infoLeft: {
    flex: 1,
  },
  infoText: {
    fontSize: 12,
    color: '#666',
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    paddingBottom: 20,
  },
  logLine: {
    paddingHorizontal: 12,
    paddingVertical: 2,
  },
  logText: {
    fontSize: 11,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    lineHeight: 16,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 12,
    fontSize: 14,
    color: '#666',
  },
  loadingMoreContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 12,
    backgroundColor: '#111',
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
  loadingMoreText: {
    marginLeft: 8,
    fontSize: 12,
    color: '#666',
  },
  latestButton: {
    backgroundColor: '#4A90E2',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 4,
    marginLeft: 8,
  },
  latestButtonText: {
    color: '#FFFFFF',
    fontSize: 12,
    fontWeight: '600',
  },
});

export default ServerLogViewer;