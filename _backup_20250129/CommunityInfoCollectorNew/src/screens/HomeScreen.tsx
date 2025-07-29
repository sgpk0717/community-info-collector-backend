import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TextInput,
  TouchableOpacity,
  SafeAreaView,
  ActivityIndicator,
  Alert,
  Image,
} from 'react-native';
import Icon from 'react-native-vector-icons/Ionicons';

interface HomeScreenProps {
  userNickname: string;
  apiBaseUrl: string;
}

type ReportLength = 'simple' | 'moderate' | 'detailed';
type TimePeriod = '1hour' | '3hours' | '12hours' | '24hours' | '3days' | '1week';
type DataSource = 'reddit' | 'twitter';

interface DataSourceInfo {
  id: DataSource;
  name: string;
  icon: string;
  isActive: boolean;
}

export default function HomeScreen({ userNickname, apiBaseUrl }: HomeScreenProps) {
  const [keyword, setKeyword] = useState('');
  const [reportLength, setReportLength] = useState<ReportLength>('moderate');
  const [timePeriod, setTimePeriod] = useState<TimePeriod>('24hours');
  const [selectedSources, setSelectedSources] = useState<DataSource[]>(['reddit']);
  const [isLoading, setIsLoading] = useState(false);
  const [twitterApiStatus, setTwitterApiStatus] = useState({
    used: 0,
    limit: 50000,
    resetDate: new Date().toISOString().split('T')[0],
  });

  const reportLengthOptions = [
    { id: 'simple', label: '간단' },
    { id: 'moderate', label: '보통' },
    { id: 'detailed', label: '상세' },
  ] as const;

  const timePeriodOptions = [
    { id: '1hour', label: '1시간' },
    { id: '3hours', label: '3시간' },
    { id: '12hours', label: '12시간' },
    { id: '24hours', label: '24시간' },
    { id: '3days', label: '3일' },
    { id: '1week', label: '1주일' },
  ] as const;

  const dataSources: DataSourceInfo[] = [
    { id: 'reddit', name: 'Reddit', icon: 'logo-reddit', isActive: true },
    { id: 'twitter', name: 'X (Twitter)', icon: 'logo-twitter', isActive: true },
  ];

  useEffect(() => {
    fetchXApiUsage();
  }, []);

  const fetchXApiUsage = async () => {
    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/x-api-usage`);
      if (response.ok) {
        const data = await response.json();
        setTwitterApiStatus({
          used: data.used,
          limit: data.limit,
          resetDate: data.reset_date,
        });
      }
    } catch (error) {
      console.error('X API 사용량 조회 실패:', error);
    }
  };

  const toggleDataSource = (source: DataSource) => {
    setSelectedSources(prev => {
      if (prev.includes(source)) {
        if (prev.length === 1) {
          Alert.alert('알림', '최소 하나의 데이터 소스를 선택해야 합니다.');
          return prev;
        }
        return prev.filter(s => s !== source);
      }
      return [...prev, source];
    });
  };

  const handleAnalyze = async () => {
    if (!keyword.trim()) {
      Alert.alert('알림', '분석할 키워드를 입력해주세요.');
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(`${apiBaseUrl}/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: keyword.trim(),
          sources: selectedSources,
          user_nickname: userNickname,
          length: reportLength,
          time_filter: timePeriod,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        Alert.alert('성공', '분석이 시작되었습니다. 보고서 탭에서 확인하세요.');
        setKeyword('');
      } else {
        Alert.alert('오류', '분석 요청에 실패했습니다.');
      }
    } catch (error) {
      Alert.alert('오류', '서버 연결에 실패했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
        {/* 키워드 입력 섹션 */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>분석할 키워드</Text>
          <View style={styles.inputContainer}>
            <TextInput
              style={styles.input}
              placeholder="예: 테슬라의 미래"
              placeholderTextColor="#666666"
              value={keyword}
              onChangeText={setKeyword}
              editable={!isLoading}
            />
          </View>
        </View>

        {/* 보고서 길이 선택 */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>보고서 길이</Text>
          <View style={styles.optionContainer}>
            {reportLengthOptions.map(option => (
              <TouchableOpacity
                key={option.id}
                style={[
                  styles.optionButton,
                  reportLength === option.id && styles.optionButtonActive,
                ]}
                onPress={() => setReportLength(option.id)}
                disabled={isLoading}
              >
                <Text
                  style={[
                    styles.optionButtonText,
                    reportLength === option.id && styles.optionButtonTextActive,
                  ]}
                >
                  {option.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* 분석 기간 선택 */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>분석 기간</Text>
          <View style={styles.periodGrid}>
            {timePeriodOptions.map(option => (
              <TouchableOpacity
                key={option.id}
                style={[
                  styles.periodButton,
                  timePeriod === option.id && styles.periodButtonActive,
                ]}
                onPress={() => setTimePeriod(option.id)}
                disabled={isLoading}
              >
                <Text
                  style={[
                    styles.periodButtonText,
                    timePeriod === option.id && styles.periodButtonTextActive,
                  ]}
                >
                  {option.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* 데이터 소스 선택 */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>데이터 소스</Text>
          <View style={styles.sourceContainer}>
            {dataSources.map(source => (
              <TouchableOpacity
                key={source.id}
                style={[
                  styles.sourceCard,
                  selectedSources.includes(source.id) && styles.sourceCardActive,
                ]}
                onPress={() => toggleDataSource(source.id)}
                disabled={isLoading || !source.isActive}
              >
                <View style={styles.sourceIconContainer}>
                  <Icon name={source.icon} size={24} color="#8E8E93" />
                </View>
                <Text style={styles.sourceName}>{source.name}</Text>
                {selectedSources.includes(source.id) && (
                  <View style={styles.checkmark}>
                    <Text style={styles.checkmarkText}>✓</Text>
                  </View>
                )}
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* X API 사용량 정보 */}
        <View style={styles.apiStatusSection}>
          <View style={styles.apiStatusHeader}>
            <Text style={styles.apiStatusTitle}>X(Twitter) API 사용량</Text>
            <Text style={styles.apiStatusSubtitle}>월간 제한</Text>
          </View>
          <View style={styles.apiStatusContent}>
            <View style={styles.apiUsageBar}>
              <View
                style={[
                  styles.apiUsageProgress,
                  { width: `${(twitterApiStatus.used / twitterApiStatus.limit) * 100}%` },
                ]}
              />
            </View>
            <View style={styles.apiUsageInfo}>
              <Text style={styles.apiUsageText}>
                {twitterApiStatus.used.toLocaleString()} / {twitterApiStatus.limit.toLocaleString()}
              </Text>
              <Text style={styles.apiResetText}>리셋: {twitterApiStatus.resetDate}</Text>
            </View>
          </View>
        </View>

        {/* 분석 시작 버튼 */}
        <TouchableOpacity
          style={[styles.analyzeButton, isLoading && styles.analyzeButtonDisabled]}
          onPress={handleAnalyze}
          disabled={isLoading || !keyword.trim()}
        >
          {isLoading ? (
            <ActivityIndicator color="#FFFFFF" />
          ) : (
            <Text style={styles.analyzeButtonText}>분석 시작</Text>
          )}
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000000',
  },
  scrollView: {
    flex: 1,
    paddingHorizontal: 16,
  },
  section: {
    marginTop: 24,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
    marginBottom: 12,
  },
  inputContainer: {
    backgroundColor: '#1C1C1E',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#333333',
  },
  input: {
    fontSize: 16,
    color: '#FFFFFF',
    paddingVertical: 16,
    paddingHorizontal: 16,
  },
  optionContainer: {
    flexDirection: 'row',
    gap: 8,
  },
  optionButton: {
    flex: 1,
    backgroundColor: '#1C1C1E',
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#333333',
  },
  optionButtonActive: {
    backgroundColor: '#007AFF',
    borderColor: '#007AFF',
  },
  optionButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#8E8E93',
  },
  optionButtonTextActive: {
    color: '#FFFFFF',
  },
  periodGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  periodButton: {
    width: '31%',
    backgroundColor: '#1C1C1E',
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#333333',
  },
  periodButtonActive: {
    backgroundColor: '#007AFF',
    borderColor: '#007AFF',
  },
  periodButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#8E8E93',
  },
  periodButtonTextActive: {
    color: '#FFFFFF',
  },
  sourceContainer: {
    flexDirection: 'row',
    gap: 12,
  },
  sourceCard: {
    flex: 1,
    backgroundColor: '#1C1C1E',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#333333',
    position: 'relative',
  },
  sourceCardActive: {
    borderColor: '#007AFF',
    backgroundColor: '#0A0A0A',
  },
  sourceIconContainer: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#2C2C2E',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 8,
  },
  sourceIcon: {
    fontSize: 24,
    fontWeight: '700',
    color: '#8E8E93',
  },
  sourceName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  checkmark: {
    position: 'absolute',
    top: 8,
    right: 8,
    width: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: '#007AFF',
    justifyContent: 'center',
    alignItems: 'center',
  },
  checkmarkText: {
    color: '#FFFFFF',
    fontSize: 12,
    fontWeight: 'bold',
  },
  apiStatusSection: {
    marginTop: 24,
    backgroundColor: '#1C1C1E',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#333333',
  },
  apiStatusHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  apiStatusTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  apiStatusSubtitle: {
    fontSize: 12,
    color: '#8E8E93',
  },
  apiStatusContent: {
    gap: 8,
  },
  apiUsageBar: {
    height: 8,
    backgroundColor: '#333333',
    borderRadius: 4,
    overflow: 'hidden',
  },
  apiUsageProgress: {
    height: '100%',
    backgroundColor: '#007AFF',
  },
  apiUsageInfo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  apiUsageText: {
    fontSize: 12,
    color: '#8E8E93',
  },
  apiResetText: {
    fontSize: 12,
    color: '#8E8E93',
  },
  analyzeButton: {
    backgroundColor: '#007AFF',
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
    marginTop: 32,
    marginBottom: 32,
  },
  analyzeButtonDisabled: {
    opacity: 0.5,
  },
  analyzeButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
  },
});