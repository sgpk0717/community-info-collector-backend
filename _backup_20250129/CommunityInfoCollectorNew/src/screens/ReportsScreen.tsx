import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  SafeAreaView,
  ActivityIndicator,
  RefreshControl,
  Alert,
  Animated,
  PanResponder,
} from 'react-native';
import Icon from 'react-native-vector-icons/Ionicons';
import ReportRenderer from '../components/ReportRenderer';

interface ReportsScreenProps {
  userNickname: string;
  apiBaseUrl: string;
}

interface Report {
  id: string;
  query_text: string;
  created_at: string;
  summary: string;
  full_report?: string;
  time_filter?: string;
  posts_collected: number;
  report_length?: string;
}

interface SwipeableItemProps {
  report: Report;
  onPress: () => void;
  onDelete: () => void;
  isSelected: boolean;
  onLongPress: () => void;
  isSelectionMode: boolean;
  onToggleSelect: () => void;
}

const TIME_FILTER_LABELS: Record<string, string> = {
  '1hour': '1시간',
  '3hours': '3시간',
  '12hours': '12시간',
  '24hours': '24시간',
  '3days': '3일',
  '1week': '1주일',
};

const REPORT_LENGTH_LABELS: Record<string, string> = {
  'simple': '간단',
  'moderate': '보통',
  'detailed': '상세',
};

const SwipeableReportCard: React.FC<SwipeableItemProps> = ({
  report,
  onPress,
  onDelete,
  isSelected,
  onLongPress,
  isSelectionMode,
  onToggleSelect,
}) => {
  const swipeAnim = useRef(new Animated.Value(0)).current;
  const [isSwiping, setIsSwiping] = useState(false);

  const panResponder = PanResponder.create({
    onMoveShouldSetPanResponder: (evt, gestureState) => {
      return Math.abs(gestureState.dx) > 10 && !isSelectionMode;
    },
    onPanResponderMove: (evt, gestureState) => {
      if (gestureState.dx < 0) {
        setIsSwiping(true);
        swipeAnim.setValue(Math.max(gestureState.dx, -80));
      }
    },
    onPanResponderRelease: (evt, gestureState) => {
      if (gestureState.dx < -50) {
        Animated.spring(swipeAnim, {
          toValue: -80,
          useNativeDriver: false,
        }).start();
      } else {
        Animated.spring(swipeAnim, {
          toValue: 0,
          useNativeDriver: false,
        }).start();
        setIsSwiping(false);
      }
    },
  });

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    
    return `${year}.${month}.${day} ${hours}:${minutes}`;
  };

  const getReportLength = () => {
    if (!report.full_report) return 0;
    return report.full_report.length;
  };

  const handlePress = () => {
    if (isSelectionMode) {
      onToggleSelect();
    } else if (!isSwiping) {
      onPress();
    }
  };

  return (
    <View style={styles.swipeContainer}>
      <Animated.View
        style={[
          styles.deleteButtonContainer,
          {
            transform: [{
              translateX: swipeAnim.interpolate({
                inputRange: [-80, 0],
                outputRange: [0, 80],
              }),
            }],
            opacity: swipeAnim.interpolate({
              inputRange: [-80, -20, 0],
              outputRange: [1, 1, 0],
            }),
          },
        ]}
      >
        <TouchableOpacity
          style={styles.deleteButton}
          onPress={onDelete}
          activeOpacity={0.8}
        >
          <Icon name="trash-outline" size={24} color="#FFFFFF" />
        </TouchableOpacity>
      </Animated.View>
      
      <Animated.View
        style={[
          styles.reportCardWrapper,
          { transform: [{ translateX: swipeAnim }] },
        ]}
        {...panResponder.panHandlers}
      >
        <TouchableOpacity
          style={[
            styles.reportCard,
            isSelected && styles.reportCardSelected,
          ]}
          activeOpacity={0.7}
          onPress={handlePress}
          onLongPress={onLongPress}
        >
          {isSelectionMode && (
            <View style={styles.selectionIndicator}>
              <View style={[
                styles.checkbox,
                isSelected && styles.checkboxSelected,
              ]}>
                {isSelected && <Icon name="checkmark" size={16} color="#FFFFFF" />}
              </View>
            </View>
          )}
          
          <View style={styles.reportContent}>
            <View style={styles.reportHeader}>
              <Text style={styles.reportTitle} numberOfLines={1}>
                {report.query_text}
              </Text>
              <View style={styles.badgeContainer}>
                {report.time_filter && (
                  <View style={styles.timeBadge}>
                    <Text style={styles.timeBadgeText}>
                      {TIME_FILTER_LABELS[report.time_filter] || report.time_filter}
                    </Text>
                  </View>
                )}
                {report.report_length && (
                  <View style={[styles.lengthBadge, styles[`lengthBadge_${report.report_length}`]]}>
                    <Text style={styles.lengthBadgeText}>
                      {REPORT_LENGTH_LABELS[report.report_length] || report.report_length}
                    </Text>
                  </View>
                )}
              </View>
            </View>
            
            <Text style={styles.reportSummary} numberOfLines={2}>
              {report.summary}
            </Text>
            
            <View style={styles.reportFooter}>
              <Text style={styles.reportDate}>{formatDate(report.created_at)}</Text>
              <View style={styles.reportStats}>
                <View style={styles.statItem}>
                  <Icon name="document-text-outline" size={14} color="#8E8E93" />
                  <Text style={styles.statText}>{report.posts_collected}</Text>
                </View>
                <View style={styles.statDivider} />
                <View style={styles.statItem}>
                  <Icon name="text-outline" size={14} color="#8E8E93" />
                  <Text style={styles.statText}>{getReportLength().toLocaleString()}</Text>
                </View>
              </View>
            </View>
          </View>
        </TouchableOpacity>
      </Animated.View>
    </View>
  );
};

export default function ReportsScreen({ userNickname, apiBaseUrl }: ReportsScreenProps) {
  const [reports, setReports] = useState<Report[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [selectedReports, setSelectedReports] = useState<Set<string>>(new Set());
  const [isSelectionMode, setIsSelectionMode] = useState(false);
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [showReportDetail, setShowReportDetail] = useState(false);

  useEffect(() => {
    fetchReports();
  }, []);

  const fetchReports = async (isRefresh = false) => {
    if (isRefresh) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }

    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/reports/${userNickname}`);
      if (response.ok) {
        const data = await response.json();
        setReports(data.reports || []);
      } else {
        Alert.alert('오류', '보고서를 불러오는데 실패했습니다.');
      }
    } catch (error) {
      Alert.alert('오류', '서버 연결에 실패했습니다.');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  const handleDeleteReport = async (reportId: string) => {
    Alert.alert(
      '보고서 삭제',
      '이 보고서를 삭제하시겠습니까?',
      [
        { text: '취소', style: 'cancel' },
        {
          text: '삭제',
          style: 'destructive',
          onPress: async () => {
            try {
              const response = await fetch(`${apiBaseUrl}/api/v1/reports/${reportId}`, {
                method: 'DELETE',
              });
              
              if (response.ok) {
                setReports(prev => prev.filter(r => r.id !== reportId));
                if (selectedReports.has(reportId)) {
                  setSelectedReports(prev => {
                    const newSet = new Set(prev);
                    newSet.delete(reportId);
                    return newSet;
                  });
                }
              } else {
                Alert.alert('오류', '보고서 삭제에 실패했습니다.');
              }
            } catch (error) {
              Alert.alert('오류', '서버 연결에 실패했습니다.');
            }
          },
        },
      ],
    );
  };

  const handleBulkDelete = () => {
    if (selectedReports.size === 0) {
      Alert.alert('알림', '삭제할 보고서를 선택해주세요.');
      return;
    }

    Alert.alert(
      '보고서 일괄 삭제',
      `선택한 ${selectedReports.size}개의 보고서를 삭제하시겠습니까?`,
      [
        { text: '취소', style: 'cancel' },
        {
          text: '삭제',
          style: 'destructive',
          onPress: async () => {
            try {
              const deletePromises = Array.from(selectedReports).map(reportId =>
                fetch(`${apiBaseUrl}/api/v1/reports/${reportId}`, { method: 'DELETE' })
              );
              
              await Promise.all(deletePromises);
              
              setReports(prev => prev.filter(r => !selectedReports.has(r.id)));
              setSelectedReports(new Set());
              setIsSelectionMode(false);
            } catch (error) {
              Alert.alert('오류', '일부 보고서 삭제에 실패했습니다.');
            }
          },
        },
      ],
    );
  };

  const toggleSelectReport = (reportId: string) => {
    setSelectedReports(prev => {
      const newSet = new Set(prev);
      if (newSet.has(reportId)) {
        newSet.delete(reportId);
      } else {
        newSet.add(reportId);
      }
      return newSet;
    });
  };

  const enterSelectionMode = () => {
    setIsSelectionMode(true);
  };

  const exitSelectionMode = () => {
    setIsSelectionMode(false);
    setSelectedReports(new Set());
  };

  const renderReport = ({ item }: { item: Report }) => (
    <SwipeableReportCard
      report={item}
      onPress={() => {
        setSelectedReport(item);
        setShowReportDetail(true);
      }}
      onDelete={() => handleDeleteReport(item.id)}
      isSelected={selectedReports.has(item.id)}
      onLongPress={enterSelectionMode}
      isSelectionMode={isSelectionMode}
      onToggleSelect={() => toggleSelectReport(item.id)}
    />
  );

  const renderEmpty = () => (
    <View style={styles.emptyContainer}>
      <Text style={styles.emptyIcon}>📋</Text>
      <Text style={styles.emptyText}>아직 생성된 보고서가 없습니다</Text>
      <Text style={styles.emptySubtext}>실시간 분석 탭에서 첫 보고서를 만들어보세요</Text>
    </View>
  );

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      {isSelectionMode ? (
        <View style={styles.selectionHeader}>
          <TouchableOpacity onPress={exitSelectionMode} style={styles.cancelButton}>
            <Text style={styles.cancelButtonText}>취소</Text>
          </TouchableOpacity>
          <Text style={styles.selectionCount}>{selectedReports.size}개 선택됨</Text>
          <TouchableOpacity onPress={handleBulkDelete} style={styles.deleteTextButton}>
            <Text style={styles.deleteTextButtonText}>삭제</Text>
          </TouchableOpacity>
        </View>
      ) : (
        reports.length > 0 && (
          <View style={styles.normalHeader}>
            <Text style={styles.headerTitle}>보고서 목록</Text>
            <TouchableOpacity 
              onPress={enterSelectionMode} 
              style={styles.editButton}
            >
              <Icon name="checkmark-circle-outline" size={24} color="#007AFF" />
            </TouchableOpacity>
          </View>
        )
      )}
      
      <FlatList
        data={reports}
        renderItem={renderReport}
        keyExtractor={item => item.id}
        contentContainerStyle={styles.listContent}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={isRefreshing}
            onRefresh={() => fetchReports(true)}
            tintColor="#007AFF"
          />
        }
        ListEmptyComponent={renderEmpty}
      />
      
      {/* 보고서 상세 화면 */}
      {selectedReport && (
        <ReportRenderer
          visible={showReportDetail}
          report={selectedReport}
          onClose={() => {
            setShowReportDetail(false);
            setSelectedReport(null);
          }}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000000',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#000000',
  },
  normalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#333333',
    backgroundColor: '#000000',
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  editButton: {
    padding: 8,
  },
  selectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#333333',
    backgroundColor: '#000000',
  },
  cancelButton: {
    padding: 8,
  },
  cancelButtonText: {
    color: '#007AFF',
    fontSize: 16,
  },
  selectionCount: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
  deleteTextButton: {
    padding: 8,
  },
  deleteTextButtonText: {
    color: '#FF3B30',
    fontSize: 16,
    fontWeight: '600',
  },
  listContent: {
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 32,
  },
  swipeContainer: {
    marginBottom: 12,
    position: 'relative',
    overflow: 'hidden',
  },
  deleteButtonContainer: {
    position: 'absolute',
    right: 0,
    top: 0,
    bottom: 0,
    width: 80,
    justifyContent: 'center',
    alignItems: 'center',
  },
  deleteButton: {
    backgroundColor: '#FF3B30',
    width: 64,
    height: '100%',
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 12,
  },
  reportCardWrapper: {
    backgroundColor: '#000000',
  },
  reportCard: {
    backgroundColor: '#1C1C1E',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#333333',
    flexDirection: 'row',
    alignItems: 'center',
  },
  reportCardSelected: {
    borderColor: '#007AFF',
    backgroundColor: '#0A0A0A',
  },
  selectionIndicator: {
    marginRight: 12,
  },
  checkbox: {
    width: 24,
    height: 24,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: '#8E8E93',
    justifyContent: 'center',
    alignItems: 'center',
  },
  checkboxSelected: {
    backgroundColor: '#007AFF',
    borderColor: '#007AFF',
  },
  reportContent: {
    flex: 1,
  },
  reportHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  reportTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#FFFFFF',
    flex: 1,
    marginRight: 8,
  },
  badgeContainer: {
    flexDirection: 'row',
    gap: 6,
  },
  timeBadge: {
    backgroundColor: '#87CEEB',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
  },
  timeBadgeText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#333333',
  },
  lengthBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
  },
  lengthBadge_simple: {
    backgroundColor: '#A8E6CF',
  },
  lengthBadge_moderate: {
    backgroundColor: '#FFE5B4',
  },
  lengthBadge_detailed: {
    backgroundColor: '#B4A7D6',
  },
  lengthBadgeText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#333333',
  },
  reportSummary: {
    fontSize: 14,
    color: '#8E8E93',
    lineHeight: 20,
    marginBottom: 12,
  },
  reportFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  reportDate: {
    fontSize: 12,
    color: '#8E8E93',
  },
  reportStats: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  statItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  statText: {
    fontSize: 12,
    color: '#8E8E93',
  },
  statDivider: {
    width: 1,
    height: 12,
    backgroundColor: '#3C3C3E',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingTop: 100,
  },
  emptyIcon: {
    fontSize: 60,
    marginBottom: 16,
  },
  emptyText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#FFFFFF',
    marginBottom: 8,
  },
  emptySubtext: {
    fontSize: 14,
    color: '#8E8E93',
    textAlign: 'center',
    paddingHorizontal: 32,
  },
});