import React, { useEffect, useState } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  SafeAreaView, 
  ActivityIndicator,
  TouchableOpacity 
} from 'react-native';
import { useRoute, useNavigation } from '@react-navigation/native';
import ReportRenderer from '../components/ReportRenderer';
import { api } from '../services/api';

interface RouteParams {
  reportId: string;
}

interface Report {
  id: string;
  query_text: string;
  full_report: string;
  summary: string;
  created_at: string;
  posts_collected: number;
}

interface ReportLink {
  footnote_number: number;
  url: string;
  title: string;
  score: number;
  comments: number;
  subreddit: string;
  author: string;
  created_utc: string;
}

export default function ReportDetailScreen() {
  const route = useRoute();
  const navigation = useNavigation();
  const { reportId } = route.params as RouteParams;
  
  const [report, setReport] = useState<Report | null>(null);
  const [reportLinks, setReportLinks] = useState<ReportLink[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchReportDetails();
  }, [reportId]);

  const fetchReportDetails = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // 보고서 상세 정보 가져오기
      const reportResponse = await api.getReportDetail(reportId);
      setReport(reportResponse.data);
      
      // 보고서 링크 정보 가져오기
      const linksResponse = await api.getReportLinks(reportId);
      setReportLinks(linksResponse.data || []);
    } catch (err) {
      console.error('Error fetching report details:', err);
      setError('보고서를 불러오는데 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#007AFF" />
          <Text style={styles.loadingText}>보고서 불러오는 중...</Text>
        </View>
      </SafeAreaView>
    );
  }

  if (error || !report) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.errorContainer}>
          <Text style={styles.errorText}>{error || '보고서를 찾을 수 없습니다.'}</Text>
          <TouchableOpacity 
            style={styles.retryButton}
            onPress={fetchReportDetails}
          >
            <Text style={styles.retryButtonText}>다시 시도</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity 
          style={styles.backButton}
          onPress={() => navigation.goBack()}
        >
          <Text style={styles.backButtonText}>‹ 뒤로</Text>
        </TouchableOpacity>
        <View style={styles.headerInfo}>
          <Text style={styles.queryText}>{report.query_text}</Text>
          <Text style={styles.dateText}>
            {new Date(report.created_at).toLocaleDateString('ko-KR')}
          </Text>
        </View>
      </View>
      
      <ReportRenderer 
        fullReport={report.full_report}
        reportLinks={reportLinks}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
  header: {
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E5EA',
  },
  backButton: {
    marginBottom: 12,
  },
  backButtonText: {
    fontSize: 17,
    color: '#007AFF',
  },
  headerInfo: {
    marginLeft: 8,
  },
  queryText: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#1C1C1E',
    marginBottom: 4,
  },
  dateText: {
    fontSize: 14,
    color: '#8E8E93',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    color: '#8E8E93',
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  errorText: {
    fontSize: 16,
    color: '#FF3B30',
    textAlign: 'center',
    marginBottom: 20,
  },
  retryButton: {
    paddingHorizontal: 24,
    paddingVertical: 12,
    backgroundColor: '#007AFF',
    borderRadius: 8,
  },
  retryButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
});