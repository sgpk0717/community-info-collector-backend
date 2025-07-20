import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  RefreshControl,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { BottomTabNavigationProp } from '@react-navigation/bottom-tabs';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { MainTabParamList } from '../navigation/AppNavigator';
import { STORAGE_KEYS } from '../constants/config';
import { Report } from '../types';
import api from '../services/api';

type HomeScreenNavigationProp = BottomTabNavigationProp<MainTabParamList, 'Home'>;

export default function HomeScreen() {
  const navigation = useNavigation<HomeScreenNavigationProp>();
  const [userNickname, setUserNickname] = useState<string>('');
  const [recentReports, setRecentReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadUserData();
  }, []);

  const loadUserData = async () => {
    try {
      const nickname = await AsyncStorage.getItem(STORAGE_KEYS.USER_NICKNAME);
      if (nickname) {
        setUserNickname(nickname);
        await loadRecentReports(nickname);
      }
    } catch (error) {
      console.error('Failed to load user data:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadRecentReports = async (nickname: string) => {
    try {
      const reports = await api.getReports(nickname);
      setRecentReports(reports.slice(0, 5)); // 최근 5개만
    } catch (error) {
      console.error('Failed to load reports:', error);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    if (userNickname) {
      await loadRecentReports(userNickname);
    }
    setRefreshing(false);
  };

  const navigateToSearch = () => {
    navigation.navigate('Search');
  };

  const navigateToReports = () => {
    navigation.navigate('Reports');
  };

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }
    >
      <View style={styles.header}>
        <Text style={styles.greeting}>안녕하세요, {userNickname}님!</Text>
        <Text style={styles.subtitle}>오늘은 어떤 정보를 찾아볼까요?</Text>
      </View>

      <TouchableOpacity style={styles.searchButton} onPress={navigateToSearch}>
        <Text style={styles.searchButtonText}>새로운 검색 시작하기</Text>
      </TouchableOpacity>

      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>최근 보고서</Text>
          <TouchableOpacity onPress={navigateToReports}>
            <Text style={styles.seeAllText}>전체보기</Text>
          </TouchableOpacity>
        </View>

        {loading ? (
          <Text style={styles.loadingText}>로딩 중...</Text>
        ) : recentReports.length > 0 ? (
          recentReports.map((report) => (
            <TouchableOpacity
              key={report.id}
              style={styles.reportCard}
              onPress={() => {
                // 나중에 구현: 보고서 상세 화면으로 이동
              }}
            >
              <Text style={styles.reportTitle}>{report.query_text}</Text>
              <Text style={styles.reportSummary} numberOfLines={2}>
                {report.summary}
              </Text>
              <View style={styles.reportMeta}>
                <Text style={styles.reportMetaText}>
                  {new Date(report.created_at).toLocaleDateString('ko-KR')}
                </Text>
                <Text style={styles.reportMetaText}>
                  {report.posts_collected}개 게시물 분석
                </Text>
              </View>
            </TouchableOpacity>
          ))
        ) : (
          <Text style={styles.emptyText}>
            아직 생성된 보고서가 없습니다.{'\n'}
            새로운 검색을 시작해보세요!
          </Text>
        )}
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>빠른 메뉴</Text>
        <View style={styles.quickMenu}>
          <TouchableOpacity 
            style={styles.quickMenuItem}
            onPress={() => navigation.navigate('Schedule')}
          >
            <Text style={styles.quickMenuIcon}>⏰</Text>
            <Text style={styles.quickMenuText}>스케줄 관리</Text>
          </TouchableOpacity>
          <TouchableOpacity 
            style={styles.quickMenuItem}
            onPress={() => navigation.navigate('Settings')}
          >
            <Text style={styles.quickMenuIcon}>⚙️</Text>
            <Text style={styles.quickMenuText}>설정</Text>
          </TouchableOpacity>
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F2F2F7',
  },
  header: {
    backgroundColor: '#FFFFFF',
    paddingHorizontal: 20,
    paddingTop: 60,
    paddingBottom: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E5EA',
  },
  greeting: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#000000',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 16,
    color: '#666666',
  },
  searchButton: {
    margin: 20,
    backgroundColor: '#007AFF',
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
  },
  searchButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
  section: {
    marginBottom: 20,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    marginBottom: 12,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#000000',
  },
  seeAllText: {
    fontSize: 14,
    color: '#007AFF',
  },
  reportCard: {
    backgroundColor: '#FFFFFF',
    marginHorizontal: 20,
    marginBottom: 10,
    padding: 16,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  reportTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#000000',
    marginBottom: 6,
  },
  reportSummary: {
    fontSize: 14,
    color: '#666666',
    lineHeight: 20,
    marginBottom: 8,
  },
  reportMeta: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  reportMetaText: {
    fontSize: 12,
    color: '#8E8E93',
  },
  loadingText: {
    textAlign: 'center',
    color: '#666666',
    marginVertical: 20,
  },
  emptyText: {
    textAlign: 'center',
    color: '#666666',
    marginVertical: 30,
    lineHeight: 20,
  },
  quickMenu: {
    flexDirection: 'row',
    paddingHorizontal: 20,
    gap: 12,
  },
  quickMenuItem: {
    flex: 1,
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 20,
    alignItems: 'center',
  },
  quickMenuIcon: {
    fontSize: 32,
    marginBottom: 8,
  },
  quickMenuText: {
    fontSize: 14,
    color: '#000000',
  },
});