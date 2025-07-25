import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  TouchableOpacity,
  Modal,
  SafeAreaView,
  TextInput,
  Alert,
  ScrollView,
} from 'react-native';
import { logService, LogEntry } from '../services/log.service';

interface LogViewerProps {
  visible: boolean;
  onClose: () => void;
}

const LogViewer: React.FC<LogViewerProps> = ({ visible, onClose }) => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filter, setFilter] = useState<'all' | 'info' | 'warning' | 'error'>('all');
  const [searchText, setSearchText] = useState('');
  const [selectedLog, setSelectedLog] = useState<LogEntry | null>(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);

  useEffect(() => {
    setLogs(logService.getLogs());
    
    const unsubscribe = logService.subscribe((newLogs) => {
      setLogs(newLogs);
    });

    return unsubscribe;
  }, []);

  const filteredLogs = logs.filter(log => {
    const matchesFilter = filter === 'all' || log.level === filter;
    const matchesSearch = !searchText || 
      log.message.toLowerCase().includes(searchText.toLowerCase()) ||
      (log.details && JSON.stringify(log.details).toLowerCase().includes(searchText.toLowerCase()));
    
    return matchesFilter && matchesSearch;
  });

  const getLogColor = (level: LogEntry['level']) => {
    switch (level) {
      case 'error':
        return '#FF3B30';
      case 'warning':
        return '#FF9500';
      case 'info':
      default:
        return '#4A90E2';
    }
  };

  const renderLogItem = ({ item }: { item: LogEntry }) => {
    const color = getLogColor(item.level);
    
    return (
      <TouchableOpacity
        style={styles.logItem}
        onPress={() => {
          setSelectedLog(item);
          setDetailModalVisible(true);
        }}
      >
        <View style={styles.logHeader}>
          <View style={[styles.logLevelIndicator, { backgroundColor: color }]} />
          <Text style={styles.logTime}>
            {logService.formatLogDate(item.timestamp)} {logService.formatLogTime(item.timestamp)}
          </Text>
          <Text style={[styles.logLevel, { color }]}>
            {item.level.toUpperCase()}
          </Text>
        </View>
        <Text style={styles.logMessage} numberOfLines={2}>
          {item.message}
        </Text>
        {item.details && (
          <Text style={styles.logDetails}>
            자세히 보려면 탭하세요
          </Text>
        )}
      </TouchableOpacity>
    );
  };

  return (
    <>
      <Modal
        visible={visible}
        animationType="slide"
        onRequestClose={onClose}
      >
        <SafeAreaView style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.title}>로그 뷰어</Text>
          <TouchableOpacity onPress={onClose} style={styles.closeButton}>
            <Text style={styles.closeButtonText}>닫기</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.searchContainer}>
          <TextInput
            style={styles.searchInput}
            placeholder="로그 검색..."
            placeholderTextColor="#666"
            value={searchText}
            onChangeText={setSearchText}
          />
        </View>

        <View style={styles.filterContainer}>
          <TouchableOpacity
            style={[styles.filterButton, filter === 'all' && styles.filterButtonActive]}
            onPress={() => setFilter('all')}
          >
            <Text style={[styles.filterButtonText, filter === 'all' && styles.filterButtonTextActive]}>
              전체
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.filterButton, filter === 'info' && styles.filterButtonActive]}
            onPress={() => setFilter('info')}
          >
            <Text style={[styles.filterButtonText, filter === 'info' && styles.filterButtonTextActive]}>
              정보
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.filterButton, filter === 'warning' && styles.filterButtonActive]}
            onPress={() => setFilter('warning')}
          >
            <Text style={[styles.filterButtonText, filter === 'warning' && styles.filterButtonTextActive]}>
              경고
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.filterButton, filter === 'error' && styles.filterButtonActive]}
            onPress={() => setFilter('error')}
          >
            <Text style={[styles.filterButtonText, filter === 'error' && styles.filterButtonTextActive]}>
              에러
            </Text>
          </TouchableOpacity>
        </View>

        <View style={styles.logStats}>
          <Text style={styles.logStatsText}>
            총 {filteredLogs.length}개의 로그
          </Text>
          <TouchableOpacity
            onPress={() => {
              Alert.alert(
                '로그 삭제',
                '모든 로그를 삭제하시겠습니까?',
                [
                  { text: '취소', style: 'cancel' },
                  {
                    text: '삭제',
                    style: 'destructive',
                    onPress: () => logService.clearLogs(),
                  },
                ]
              );
            }}
          >
            <Text style={styles.clearButton}>전체 삭제</Text>
          </TouchableOpacity>
        </View>

        <FlatList
          data={filteredLogs}
          keyExtractor={(item) => item.id}
          renderItem={renderLogItem}
          contentContainerStyle={styles.listContent}
          ListEmptyComponent={
            <View style={styles.emptyContainer}>
              <Text style={styles.emptyText}>로그가 없습니다</Text>
            </View>
          }
        />
      </SafeAreaView>
    </Modal>

    {/* 로그 상세 정보 모달 */}
    <Modal
      visible={detailModalVisible}
      animationType="slide"
      transparent={true}
      onRequestClose={() => setDetailModalVisible(false)}
    >
      <View style={styles.detailModalOverlay}>
        <View style={styles.detailModalContent}>
          <View style={styles.detailModalHeader}>
            <Text style={styles.detailModalTitle}>로그 상세 정보</Text>
            <TouchableOpacity
              onPress={() => setDetailModalVisible(false)}
              style={styles.detailCloseButton}
            >
              <Text style={styles.detailCloseButtonText}>✕</Text>
            </TouchableOpacity>
          </View>
          
          {selectedLog && (
            <ScrollView style={styles.detailModalBody}>
              <View style={styles.detailSection}>
                <Text style={styles.detailLabel}>시간</Text>
                <Text style={styles.detailValue}>
                  {logService.formatLogDate(selectedLog.timestamp)} {logService.formatLogTime(selectedLog.timestamp)}
                </Text>
              </View>
              
              <View style={styles.detailSection}>
                <Text style={styles.detailLabel}>레벨</Text>
                <Text style={[styles.detailValue, { color: getLogColor(selectedLog.level) }]}>
                  {selectedLog.level.toUpperCase()}
                </Text>
              </View>
              
              <View style={styles.detailSection}>
                <Text style={styles.detailLabel}>메시지</Text>
                <Text style={styles.detailValue}>{selectedLog.message}</Text>
              </View>
              
              {selectedLog.details && (
                <View style={styles.detailSection}>
                  <Text style={styles.detailLabel}>상세 정보</Text>
                  <View style={styles.detailJsonContainer}>
                    <Text style={styles.detailJson}>
                      {JSON.stringify(selectedLog.details, null, 2)}
                    </Text>
                  </View>
                </View>
              )}
            </ScrollView>
          )}
        </View>
      </View>
    </Modal>
    </>
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
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#1A1A1A',
  },
  title: {
    fontSize: 20,
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
  searchContainer: {
    paddingHorizontal: 20,
    paddingVertical: 12,
  },
  searchInput: {
    height: 40,
    backgroundColor: '#1A1A1A',
    borderRadius: 8,
    paddingHorizontal: 16,
    fontSize: 14,
    color: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#333',
  },
  filterContainer: {
    flexDirection: 'row',
    paddingHorizontal: 20,
    marginBottom: 12,
  },
  filterButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: '#1A1A1A',
    marginRight: 8,
    borderWidth: 1,
    borderColor: '#333',
  },
  filterButtonActive: {
    backgroundColor: '#4A90E2',
    borderColor: '#4A90E2',
  },
  filterButtonText: {
    fontSize: 14,
    color: '#666',
  },
  filterButtonTextActive: {
    color: '#FFFFFF',
  },
  logStats: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#1A1A1A',
  },
  logStatsText: {
    fontSize: 12,
    color: '#666',
  },
  clearButton: {
    fontSize: 12,
    color: '#FF3B30',
  },
  listContent: {
    paddingBottom: 20,
  },
  logItem: {
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#1A1A1A',
  },
  logHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  logLevelIndicator: {
    width: 4,
    height: 16,
    borderRadius: 2,
    marginRight: 8,
  },
  logTime: {
    fontSize: 12,
    color: '#666',
    flex: 1,
  },
  logLevel: {
    fontSize: 12,
    fontWeight: '600',
  },
  logMessage: {
    fontSize: 14,
    color: '#FFFFFF',
    marginLeft: 12,
  },
  logDetails: {
    fontSize: 12,
    color: '#666',
    marginLeft: 12,
    marginTop: 4,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 100,
  },
  emptyText: {
    fontSize: 16,
    color: '#666',
  },
  detailModalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  detailModalContent: {
    backgroundColor: '#1A1A1A',
    borderRadius: 16,
    width: '90%',
    maxHeight: '80%',
    borderWidth: 1,
    borderColor: '#333',
  },
  detailModalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
  detailModalTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  detailCloseButton: {
    padding: 8,
  },
  detailCloseButtonText: {
    fontSize: 24,
    color: '#666',
  },
  detailModalBody: {
    padding: 20,
  },
  detailSection: {
    marginBottom: 20,
  },
  detailLabel: {
    fontSize: 12,
    color: '#666',
    marginBottom: 4,
    textTransform: 'uppercase',
  },
  detailValue: {
    fontSize: 14,
    color: '#FFFFFF',
    lineHeight: 20,
  },
  detailJsonContainer: {
    backgroundColor: '#000',
    borderRadius: 8,
    padding: 12,
    borderWidth: 1,
    borderColor: '#333',
  },
  detailJson: {
    fontSize: 12,
    color: '#4A90E2',
    fontFamily: 'monospace',
  },
});

export default LogViewer;