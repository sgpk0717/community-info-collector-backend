import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Alert,
  KeyboardAvoidingView,
  Platform,
  Modal,
  ActivityIndicator,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { STORAGE_KEYS, APP_CONFIG } from '../constants/config';
import { SearchRequest, ReportLength, ProgressUpdate } from '../types';
import api from '../services/api';
import websocket from '../services/websocket';

export default function SearchScreen() {
  const [query, setQuery] = useState('');
  const [reportLength, setReportLength] = useState<ReportLength>('moderate');
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState('');
  const [showProgressModal, setShowProgressModal] = useState(false);
  const [searchResult, setSearchResult] = useState<any>(null);

  useEffect(() => {
    return () => {
      websocket.disconnect();
    };
  }, []);

  const handleSearch = async () => {
    if (!query.trim()) {
      Alert.alert('알림', '검색어를 입력해주세요.');
      return;
    }

    const userNickname = await AsyncStorage.getItem(STORAGE_KEYS.USER_NICKNAME);
    if (!userNickname) {
      Alert.alert('오류', '로그인이 필요합니다.');
      return;
    }

    setLoading(true);
    setShowProgressModal(true);
    setProgress(0);
    setProgressMessage('검색을 시작합니다...');

    try {
      const searchRequest: SearchRequest = {
        query: query.trim(),
        sources: ['reddit'],
        user_nickname: userNickname,
        length: reportLength,
        schedule_yn: 'N',
      };

      const response = await api.search(searchRequest);
      
      // WebSocket 연결로 진행상황 추적
      if (response.session_id) {
        websocket.connect(response.session_id);
        
        const unsubscribe = websocket.onMessage((update: ProgressUpdate) => {
          setProgress(update.progress);
          setProgressMessage(update.message);
          
          if (update.progress === 100) {
            setTimeout(() => {
              setShowProgressModal(false);
              showSuccessAlert(response);
              unsubscribe();
              websocket.disconnect();
            }, 1000);
          }
        });
      }
      
      setSearchResult(response);
    } catch (error) {
      console.error('Search error:', error);
      Alert.alert('오류', '검색 중 오류가 발생했습니다.');
      setShowProgressModal(false);
    } finally {
      setLoading(false);
    }
  };

  const showSuccessAlert = (response: any) => {
    Alert.alert(
      '검색 완료',
      `${response.posts_collected}개의 게시물을 분석했습니다.\n보고서가 생성되었습니다.`,
      [
        {
          text: '확인',
          onPress: () => {
            setQuery('');
            // 보고서 화면으로 이동하거나 결과 표시
          },
        },
      ]
    );
  };

  return (
    <KeyboardAvoidingView 
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView style={styles.scrollView}>
        <View style={styles.header}>
          <Text style={styles.title}>새로운 검색</Text>
          <Text style={styles.subtitle}>
            키워드를 입력하면 커뮤니티의 의견을 분석해드립니다
          </Text>
        </View>

        <View style={styles.form}>
          <Text style={styles.label}>검색 키워드</Text>
          <TextInput
            style={styles.input}
            placeholder="예: 테슬라의 미래, ChatGPT 활용법"
            value={query}
            onChangeText={setQuery}
            editable={!loading}
          />

          <Text style={styles.label}>보고서 길이</Text>
          <View style={styles.lengthOptions}>
            {APP_CONFIG.reportLengthOptions.map((option) => (
              <TouchableOpacity
                key={option.value}
                style={[
                  styles.lengthOption,
                  reportLength === option.value && styles.lengthOptionActive,
                ]}
                onPress={() => setReportLength(option.value as ReportLength)}
                disabled={loading}
              >
                <Text
                  style={[
                    styles.lengthOptionText,
                    reportLength === option.value && styles.lengthOptionTextActive,
                  ]}
                >
                  {option.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          <TouchableOpacity
            style={[styles.searchButton, loading && styles.searchButtonDisabled]}
            onPress={handleSearch}
            disabled={loading}
          >
            <Text style={styles.searchButtonText}>
              {loading ? '검색 중...' : '검색하기'}
            </Text>
          </TouchableOpacity>

          <Text style={styles.info}>
            • Reddit 커뮤니티에서 관련 게시물을 수집합니다{'\n'}
            • AI가 게시물을 분석하여 보고서를 생성합니다{'\n'}
            • 보통 1-2분 정도 소요됩니다
          </Text>
        </View>
      </ScrollView>

      <Modal
        visible={showProgressModal}
        transparent
        animationType="fade"
        onRequestClose={() => {}}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <ActivityIndicator size="large" color="#007AFF" />
            <Text style={styles.modalTitle}>분석 중...</Text>
            <Text style={styles.modalMessage}>{progressMessage}</Text>
            <View style={styles.progressBar}>
              <View 
                style={[styles.progressFill, { width: `${progress}%` }]} 
              />
            </View>
            <Text style={styles.progressText}>{progress}%</Text>
          </View>
        </View>
      </Modal>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F2F2F7',
  },
  scrollView: {
    flex: 1,
  },
  header: {
    backgroundColor: '#FFFFFF',
    paddingHorizontal: 20,
    paddingTop: 60,
    paddingBottom: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E5EA',
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#000000',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 16,
    color: '#666666',
  },
  form: {
    padding: 20,
  },
  label: {
    fontSize: 16,
    fontWeight: '600',
    color: '#000000',
    marginBottom: 8,
    marginTop: 16,
  },
  input: {
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#E5E5EA',
    borderRadius: 8,
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontSize: 16,
  },
  lengthOptions: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 24,
  },
  lengthOption: {
    flex: 1,
    paddingVertical: 12,
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#E5E5EA',
    borderRadius: 8,
    alignItems: 'center',
  },
  lengthOptionActive: {
    backgroundColor: '#007AFF',
    borderColor: '#007AFF',
  },
  lengthOptionText: {
    fontSize: 14,
    color: '#000000',
  },
  lengthOptionTextActive: {
    color: '#FFFFFF',
    fontWeight: '600',
  },
  searchButton: {
    backgroundColor: '#007AFF',
    borderRadius: 8,
    paddingVertical: 16,
    alignItems: 'center',
    marginBottom: 20,
  },
  searchButtonDisabled: {
    backgroundColor: '#C7C7CC',
  },
  searchButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
  info: {
    fontSize: 14,
    color: '#666666',
    lineHeight: 20,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalContent: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 24,
    width: '80%',
    alignItems: 'center',
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#000000',
    marginTop: 16,
    marginBottom: 8,
  },
  modalMessage: {
    fontSize: 14,
    color: '#666666',
    marginBottom: 20,
    textAlign: 'center',
  },
  progressBar: {
    width: '100%',
    height: 6,
    backgroundColor: '#E5E5EA',
    borderRadius: 3,
    overflow: 'hidden',
    marginBottom: 8,
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#007AFF',
  },
  progressText: {
    fontSize: 14,
    color: '#666666',
  },
});