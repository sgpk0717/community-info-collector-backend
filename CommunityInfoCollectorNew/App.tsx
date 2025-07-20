import React from 'react';
import {
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  View,
  TextInput,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  Animated,
  Easing,
  Modal,
  FlatList,
  Linking,
  StatusBar,
  Dimensions,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import ReportRenderer from './src/components/ReportRenderer';
import { logService } from './src/services/log.service';
import LogViewer from './src/components/LogViewer';
import DropdownMenu from './src/components/DropdownMenu';

const API_BASE_URL = 'https://community-info-collector-backend.onrender.com';
// const API_BASE_URL = 'http://localhost:8000'; // iOS 시뮬레이터용  
// const API_BASE_URL = 'http://10.0.2.2:8000'; // Android 에뮬레이터용
const { width: SCREEN_WIDTH } = Dimensions.get('window');

interface Report {
  id: string;
  query_text: string;
  summary: string;
  full_report: string;
  created_at: string;
  posts_collected: number;
  report_length: string;
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

function App(): JSX.Element {
  const [currentScreen, setCurrentScreen] = React.useState<'splash' | 'login' | 'register' | 'main' | 'reports' | 'error'>('splash');
  const [nickname, setNickname] = React.useState('');
  const [savedNickname, setSavedNickname] = React.useState('');
  const [isLoading, setIsLoading] = React.useState(false);
  const [reports, setReports] = React.useState<Report[]>([]);
  const [selectedReport, setSelectedReport] = React.useState<Report | null>(null);
  const [reportLinks, setReportLinks] = React.useState<ReportLink[]>([]);
  const [reportModalVisible, setReportModalVisible] = React.useState(false);
  const [registerNickname, setRegisterNickname] = React.useState('');
  const [nicknameError, setNicknameError] = React.useState('');
  // 키워드 분석 관련 상태
  const [keyword, setKeyword] = React.useState('');
  const [reportLength, setReportLength] = React.useState<'simple' | 'moderate' | 'detailed'>('moderate');
  const [saveNickname, setSaveNickname] = React.useState(false);
  const [logViewerVisible, setLogViewerVisible] = React.useState(false);
  const [serverError, setServerError] = React.useState<string>('');
  const [apiStatus, setApiStatus] = React.useState<string | null>(null);
  
  // Splash animation
  const fadeAnim = React.useRef(new Animated.Value(0)).current;
  const scaleAnim = React.useRef(new Animated.Value(0.8)).current;
  
  // API Status text scroll animation
  const scrollAnim = React.useRef(new Animated.Value(0)).current;

  React.useEffect(() => {
    // Splash screen animation
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 1000,
        useNativeDriver: true,
      }),
      Animated.spring(scaleAnim, {
        toValue: 1,
        friction: 4,
        useNativeDriver: true,
      }),
    ]).start();

    // 저장된 닉네임 불러오기
    loadSavedNickname();

    // 앱 시작 로그
    logService.info('앱이 시작되었습니다');

    // 서버 헬스체크 후 화면 전환
    checkServerHealth();
  }, []);

  // API Status 스크롤 애니메이션
  React.useEffect(() => {
    if (apiStatus && apiStatus.length > 40) { // 40자 이상일 때만 스크롤
      scrollAnim.setValue(0);
      Animated.loop(
        Animated.sequence([
          Animated.delay(1000), // 1초 대기
          Animated.timing(scrollAnim, {
            toValue: -SCREEN_WIDTH,
            duration: 8000, // 8초에 걸쳐 스크롤
            useNativeDriver: true,
            easing: Easing.linear,
          }),
        ]),
      ).start();
    }
  }, [apiStatus]);


  const checkServerHealth = async () => {
    const healthCheckUrl = `${API_BASE_URL}/`;
    setApiStatus(`${healthCheckUrl} 헬스체크 중...`);
    
    logService.info('서버 헬스체크 시작...');
    console.log('=== 헬스체크 시작 ===');
    console.log('API URL:', API_BASE_URL);
    console.log('헬스체크 URL:', healthCheckUrl);
    
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000); // 10초로 늘림
      
      console.log('Fetch 요청 시작...');
      const response = await fetch(healthCheckUrl, {
        method: 'GET',
        signal: controller.signal,
        headers: {
          'Accept': 'application/json',
        },
      });
      
      clearTimeout(timeoutId);
      console.log('Fetch 응답 받음:', response.status, response.statusText);
      
      if (response.ok) {
        const data = await response.json();
        logService.info('서버 헬스체크 성공', data);
        console.log('헬스체크 성공:', data);
        
        setApiStatus(`헬스체크 성공: ${data.status || 'OK'}`);
        
        // 2초 후 로그인 화면으로 이동
        setTimeout(() => {
          setApiStatus(null);
          setCurrentScreen('login');
          logService.info('로그인 화면으로 이동');
        }, 2000);
      } else {
        throw new Error(`서버 응답 오류: ${response.status} ${response.statusText}`);
      }
    } catch (error: any) {
      console.error('=== 헬스체크 오류 ===');
      console.error('Error Type:', error?.name);
      console.error('Error Message:', error?.message);
      console.error('Error Code:', error?.code);
      console.error('Error Stack:', error?.stack);
      console.error('==================');
      
      logService.error('서버 헬스체크 실패', { 
        error: error?.message,
        errorType: error?.name,
        errorCode: error?.code,
        url: API_BASE_URL 
      });
      
      let errorMessage = '서버에 연결할 수 없습니다.\n\n';
      errorMessage += `URL: ${API_BASE_URL}\n`;
      errorMessage += `오류: ${error?.message}\n`;
      
      if (error?.message?.includes('aborted')) {
        errorMessage += '\n서버 응답 시간이 초과되었습니다.';
        setApiStatus('헬스체크 실패: 시간 초과');
      } else if (error?.message?.includes('Network request failed')) {
        errorMessage += '\n네트워크 연결을 확인해주세요.';
        setApiStatus('헬스체크 실패: 네트워크 오류');
      } else if (error?.message?.includes('SSL')) {
        errorMessage += '\nSSL 인증서 문제가 있을 수 있습니다.';
        setApiStatus('헬스체크 실패: SSL 오류');
      } else {
        setApiStatus(`헬스체크 실패: ${error?.message}`);
      }
      
      setServerError(errorMessage);
      setCurrentScreen('error');
      
      // 3초 후 상태 메시지 제거
      setTimeout(() => setApiStatus(null), 3000);
    }
  };

  const loadSavedNickname = async () => {
    try {
      const saved = await AsyncStorage.getItem('savedNickname');
      if (saved) {
        setNickname(saved);
        setSaveNickname(true);
        logService.info('저장된 닉네임을 불러왔습니다', { nickname: saved });
      }
    } catch (error) {
      logService.error('저장된 닉네임 불러오기 실패', error);
    }
  };

  const handleLogin = async () => {
    if (!nickname.trim()) {
      Alert.alert('알림', '닉네임을 입력해주세요.');
      return;
    }

    const loginUrl = `${API_BASE_URL}/api/v1/users/login`;
    setApiStatus(`${loginUrl} 로그인 요청 중...`);
    
    setIsLoading(true);
    logService.info('로그인 시도', { nickname: nickname.trim() });
    try {
      const response = await fetch(loginUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ user_nickname: nickname.trim() }),
      });

      if (response.ok) {
        const data = await response.json();
        const trimmedNickname = nickname.trim();
        setSavedNickname(trimmedNickname);
        
        // 닉네임 저장 옵션이 체크되어 있으면 저장
        if (saveNickname) {
          await AsyncStorage.setItem('savedNickname', trimmedNickname);
        } else {
          await AsyncStorage.removeItem('savedNickname');
        }
        
        // 로그인 성공 시 LogViewer에 기록
        logService.info('로그인 성공', { nickname: trimmedNickname });
        logService.addLog(`로그인 성공: ${loginUrl}`, 'info');
        logService.addLog(`사용자: ${trimmedNickname}`, 'info');
        
        setApiStatus('로그인 성공!');
        setTimeout(() => setApiStatus(null), 1000);
        
        setCurrentScreen('main');
      } else if (response.status === 404) {
        logService.warning('로그인 실패 - 등록되지 않은 닉네임', { nickname: nickname.trim() });
        setApiStatus('로그인 실패: 등록되지 않은 닉네임');
        setTimeout(() => setApiStatus(null), 2000);
        
        Alert.alert(
          '로그인 실패', 
          '등록되지 않은 닉네임입니다.\n닉네임을 등록해주세요.',
          [
            { text: '취소', style: 'cancel' },
            { text: '닉네임 등록', onPress: () => setCurrentScreen('register') }
          ]
        );
      } else {
        logService.error('로그인 실패', { status: response.status });
        setApiStatus(`로그인 실패: ${response.status}`);
        setTimeout(() => setApiStatus(null), 2000);
        Alert.alert('오류', '로그인에 실패했습니다. 다시 시도해주세요.');
      }
    } catch (error: any) {
      logService.error('로그인 오류', error);
      Alert.alert('오류', error.message || '서버 연결에 실패했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  const checkNicknameAvailability = async () => {
    if (!registerNickname.trim()) {
      setNicknameError('닉네임을 입력해주세요.');
      return;
    }

    if (registerNickname.trim().length < 2) {
      setNicknameError('닉네임은 2자 이상이어야 합니다.');
      return;
    }

    const checkUrl = `${API_BASE_URL}/api/v1/users/check-nickname?nickname=${encodeURIComponent(registerNickname.trim())}`;
    setApiStatus(`${checkUrl} 닉네임 중복 확인 중...`);
    
    setIsLoading(true);
    setNicknameError('');

    try {
      const response = await fetch(checkUrl);
      const data = await response.json();

      if (data.is_available) {
        setNicknameError('');
        setApiStatus('닉네임 중복 확인: 사용 가능');
        Alert.alert('확인', '사용 가능한 닉네임입니다.');
      } else {
        setNicknameError('이미 사용 중인 닉네임입니다.');
        setApiStatus('닉네임 중복 확인: 이미 사용 중');
      }
      
      setTimeout(() => setApiStatus(null), 2000);
    } catch (error) {
      setNicknameError('닉네임 확인 중 오류가 발생했습니다.');
      setApiStatus('닉네임 확인 실패');
      setTimeout(() => setApiStatus(null), 2000);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegister = async () => {
    if (!registerNickname.trim()) {
      setNicknameError('닉네임을 입력해주세요.');
      return;
    }

    if (nicknameError) {
      Alert.alert('알림', '닉네임을 확인해주세요.');
      return;
    }

    const registerUrl = `${API_BASE_URL}/api/v1/users/register`;
    setApiStatus(`${registerUrl} 회원가입 요청 중...`);
    
    setIsLoading(true);
    logService.info('닉네임 등록 시도', { nickname: registerNickname.trim() });
    try {
      const response = await fetch(registerUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ user_nickname: registerNickname.trim() }),
      });

      if (response.ok) {
        // 회원가입 성공 시 LogViewer에 기록
        logService.info('닉네임 등록 성공', { nickname: registerNickname.trim() });
        logService.addLog(`회원가입 성공: ${registerUrl}`, 'info');
        logService.addLog(`새 사용자: ${registerNickname.trim()}`, 'info');
        
        setApiStatus('회원가입 성공!');
        setTimeout(() => setApiStatus(null), 1000);
        
        Alert.alert(
          '등록 완료',
          '닉네임 등록이 완료되었습니다.',
          [
            {
              text: '확인',
              onPress: () => {
                setNickname(registerNickname);
                setRegisterNickname('');
                setNicknameError('');
                setCurrentScreen('login');
              }
            }
          ]
        );
      } else {
        const data = await response.json();
        logService.error('닉네임 등록 실패', { status: response.status, detail: data.detail });
        setApiStatus(`회원가입 실패: ${data.detail || response.status}`);
        setTimeout(() => setApiStatus(null), 3000);
        Alert.alert('오류', data.detail || '닉네임 등록에 실패했습니다.');
      }
    } catch (error: any) {
      logService.error('닉네임 등록 오류', error);
      setApiStatus(`회원가입 실패: ${error.message}`);
      setTimeout(() => setApiStatus(null), 3000);
      Alert.alert('오류', '서버 연결에 실패했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchReports = async () => {
    setIsLoading(true);
    logService.info('보고서 목록 조회 시작');
    try {
      if (!savedNickname) {
        logService.warning('로그인 정보 없음');
        Alert.alert('오류', '로그인 정보가 없습니다. 다시 로그인해주세요.');
        setCurrentScreen('login');
        return;
      }
      
      const response = await fetch(`${API_BASE_URL}/api/v1/reports/${savedNickname}`);
      
      if (response.ok) {
        const data = await response.json();
        setReports(data.reports || []);
        logService.info('보고서 목록 조회 성공', { count: data.reports?.length || 0 });
      } else {
        const errorData = await response.json();
        logService.error('보고서 목록 조회 실패', { status: response.status, error: errorData });
        Alert.alert('오류', `보고서를 불러올 수 없습니다. (${response.status})`);
      }
    } catch (error: any) {
      logService.error('보고서 목록 조회 오류', error);
      Alert.alert('오류', `보고서 로딩 실패: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReportPress = async (report: Report) => {
    setSelectedReport(report);
    setIsLoading(true);
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/reports/${report.id}/links`);
      if (response.ok) {
        const data = await response.json();
        setReportLinks(data.links || []);
      }
      setReportModalVisible(true);
    } catch (error) {
      console.error('Error fetching report links:', error);
      Alert.alert('오류', '보고서 상세 정보를 불러오는데 실패했습니다.');
    } finally {
      setIsLoading(false);
    }
  };


  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // Error Screen
  if (currentScreen === 'error') {
    return (
      <SafeAreaView style={[styles.container, styles.darkContainer]}>
        <StatusBar barStyle="light-content" backgroundColor="#000000" />
        {apiStatus && (
          <View style={styles.apiStatusBar}>
            <Animated.View 
              style={[
                styles.apiStatusTextContainer,
                apiStatus.length > 40 ? {
                  transform: [{ translateX: scrollAnim }]
                } : {}
              ]}
            >
              <Text style={styles.apiStatusText}>{apiStatus}</Text>
              {apiStatus.length > 40 && (
                <Text style={styles.apiStatusText}>    {apiStatus}</Text>
              )}
            </Animated.View>
          </View>
        )}
        <View style={styles.errorContainer}>
          <Text style={styles.errorIcon}>⚠️</Text>
          <Text style={styles.errorTitle}>서버 연결 실패</Text>
          <Text style={styles.errorMessage}>{serverError}</Text>
          
          <TouchableOpacity
            style={styles.retryButton}
            onPress={() => {
              setCurrentScreen('splash');
              setTimeout(() => checkServerHealth(), 500);
            }}
          >
            <Text style={styles.retryButtonText}>다시 시도</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  // Splash Screen
  if (currentScreen === 'splash') {
    return (
      <View style={[styles.container, styles.splashContainer]}>
        <StatusBar barStyle="light-content" backgroundColor="#000000" />
        <Animated.View
          style={[
            styles.logoContainer,
            {
              opacity: fadeAnim,
              transform: [{ scale: scaleAnim }],
            },
          ]}
        >
          <View style={styles.iconContainer}>
            <Text style={styles.iconText}>💎</Text>
          </View>
          <Text style={styles.splashTitle}>Collector</Text>
          <Text style={styles.splashSubtitle}>AI 커뮤니티 분석 플랫폼</Text>
        </Animated.View>
        
        <View style={styles.splashLoadingContainer}>
          <ActivityIndicator size="small" color="#FFFFFF" />
        </View>
      </View>
    );
  }

  // Login Screen
  if (currentScreen === 'login') {
    return (
      <View style={[styles.container, styles.darkContainer]}>
        <StatusBar barStyle="light-content" backgroundColor="#000000" />
        {apiStatus && (
          <View style={styles.apiStatusBar}>
            <Animated.View 
              style={[
                styles.apiStatusTextContainer,
                apiStatus.length > 40 ? {
                  transform: [{ translateX: scrollAnim }]
                } : {}
              ]}
            >
              <Text style={styles.apiStatusText}>{apiStatus}</Text>
              {apiStatus.length > 40 && (
                <Text style={styles.apiStatusText}>    {apiStatus}</Text>
              )}
            </Animated.View>
          </View>
        )}
        <SafeAreaView style={styles.safeAreaContent}>
        <KeyboardAvoidingView 
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
          style={styles.content}
        >
          <View style={styles.loginHeader}>
            <Text style={styles.loginLogo}>💎</Text>
            <Text style={styles.loginTitle}>Collector</Text>
            <Text style={styles.loginSubtitle}>AI 커뮤니티 분석 플랫폼</Text>
          </View>
          
          <View style={styles.loginForm}>
            <View style={styles.modernInputContainer}>
              <Text style={styles.inputLabel}>닉네임</Text>
              <TextInput
                style={styles.modernInput}
                placeholder="닉네임을 입력해주세요"
                placeholderTextColor="#666"
                value={nickname}
                onChangeText={setNickname}
                autoCapitalize="none"
                autoCorrect={false}
                editable={!isLoading}
              />
            </View>
            
            <TouchableOpacity
              style={styles.checkboxContainer}
              onPress={() => setSaveNickname(!saveNickname)}
            >
              <View style={[styles.checkbox, saveNickname && styles.checkboxChecked]}>
                {saveNickname && <Text style={styles.checkmark}>✓</Text>}
              </View>
              <Text style={styles.checkboxLabel}>닉네임 저장하기</Text>
            </TouchableOpacity>
            
            <TouchableOpacity
              style={[styles.modernButton, isLoading && styles.modernButtonDisabled]}
              onPress={handleLogin}
              disabled={isLoading}
            >
              <Text style={styles.modernButtonText}>
                {isLoading ? '로그인 중...' : '로그인'}
              </Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.textButton}
              onPress={() => setCurrentScreen('register')}
              disabled={isLoading}
            >
              <Text style={styles.textButtonText}>
                처음이신가요? <Text style={styles.textButtonBold}>닉네임 등록하기</Text>
              </Text>
            </TouchableOpacity>
          </View>
        </KeyboardAvoidingView>
        </SafeAreaView>
      </View>
    );
  }

  // Register Screen
  if (currentScreen === 'register') {
    return (
      <SafeAreaView style={[styles.container, styles.darkContainer]}>
        <StatusBar barStyle="light-content" backgroundColor="#000000" />
        {apiStatus && (
          <View style={styles.apiStatusBar}>
            <Animated.View 
              style={[
                styles.apiStatusTextContainer,
                apiStatus.length > 40 ? {
                  transform: [{ translateX: scrollAnim }]
                } : {}
              ]}
            >
              <Text style={styles.apiStatusText}>{apiStatus}</Text>
              {apiStatus.length > 40 && (
                <Text style={styles.apiStatusText}>    {apiStatus}</Text>
              )}
            </Animated.View>
          </View>
        )}
        <KeyboardAvoidingView 
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
          style={styles.content}
        >
          <View style={styles.loginHeader}>
            <Text style={styles.loginLogo}>👤</Text>
            <Text style={styles.loginTitle}>닉네임 등록</Text>
            <Text style={styles.loginSubtitle}>사용하실 닉네임을 입력해주세요</Text>
          </View>
          
          <View style={styles.loginForm}>
            <View style={styles.modernInputContainer}>
              <Text style={styles.inputLabel}>닉네임</Text>
              <View style={styles.inputWithButton}>
                <TextInput
                  style={[styles.modernInput, styles.inputFlex]}
                  placeholder="2자 이상 입력해주세요"
                  placeholderTextColor="#666"
                  value={registerNickname}
                  onChangeText={(text) => {
                    setRegisterNickname(text);
                    setNicknameError('');
                  }}
                  autoCapitalize="none"
                  autoCorrect={false}
                  editable={!isLoading}
                />
                <TouchableOpacity
                  style={[styles.checkNicknameButton, isLoading && styles.checkNicknameButtonDisabled]}
                  onPress={checkNicknameAvailability}
                  disabled={isLoading || !registerNickname.trim()}
                >
                  <Text style={styles.checkNicknameButtonText}>
                    {isLoading ? '확인 중' : '중복확인'}
                  </Text>
                </TouchableOpacity>
              </View>
              {nicknameError ? (
                <Text style={styles.modernErrorText}>{nicknameError}</Text>
              ) : null}
            </View>
            
            <TouchableOpacity
              style={[styles.modernButton, (!registerNickname.trim() || !!nicknameError) && styles.modernButtonDisabled]}
              onPress={handleRegister}
              disabled={isLoading || !!nicknameError || !registerNickname.trim()}
            >
              <Text style={styles.modernButtonText}>
                {isLoading ? '등록 중...' : '등록하기'}
              </Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.textButton}
              onPress={() => {
                setCurrentScreen('login');
                setRegisterNickname('');
                setNicknameError('');
              }}
              disabled={isLoading}
            >
              <Text style={styles.textButtonText}>
                이미 계정이 있으신가요? <Text style={styles.textButtonBold}>로그인하기</Text>
              </Text>
            </TouchableOpacity>
          </View>
        </KeyboardAvoidingView>
      </SafeAreaView>
    );
  }

  // Reports Screen
  if (currentScreen === 'reports') {
    return (
      <SafeAreaView style={[styles.container, styles.darkContainer]}>
        <StatusBar barStyle="light-content" backgroundColor="#000000" />
        <View style={styles.modernHeader}>
          <TouchableOpacity
            onPress={() => setCurrentScreen('main')}
            style={styles.modernBackButton}
          >
            <Text style={styles.modernBackButtonText}>←</Text>
          </TouchableOpacity>
          <Text style={styles.modernHeaderTitle}>보고서</Text>
          <View style={{ width: 40 }} />
        </View>

        {isLoading ? (
          <View style={styles.centerLoadingContainer}>
            <ActivityIndicator size="large" color="#4A90E2" />
            <Text style={styles.modernLoadingText}>보고서를 불러오고 있어요</Text>
          </View>
        ) : (
          <FlatList
            data={reports}
            keyExtractor={(item) => item.id}
            contentContainerStyle={styles.modernListContent}
            renderItem={({ item }) => (
              <TouchableOpacity
                style={styles.modernReportCard}
                onPress={() => handleReportPress(item)}
                activeOpacity={0.7}
              >
                <View style={styles.modernReportHeader}>
                  <Text style={styles.modernQueryText} numberOfLines={1}>
                    {item.query_text}
                  </Text>
                  <View style={[styles.modernBadge, 
                    item.report_length === 'simple' && styles.simpleBadge,
                    item.report_length === 'moderate' && styles.moderateBadge,
                    item.report_length === 'detailed' && styles.detailedBadge
                  ]}>
                    <Text style={styles.modernBadgeText}>
                      {item.report_length === 'simple' && '간단'}
                      {item.report_length === 'moderate' && '보통'}
                      {item.report_length === 'detailed' && '상세'}
                    </Text>
                  </View>
                </View>

                <Text style={styles.modernSummaryText} numberOfLines={2}>
                  {item.summary}
                </Text>

                <View style={styles.modernReportFooter}>
                  <View style={styles.modernReportMeta}>
                    <Text style={styles.modernIcon}>📅</Text>
                    <Text style={styles.modernDateText}>{formatDate(item.created_at)}</Text>
                  </View>
                  <View style={styles.modernReportMeta}>
                    <Text style={styles.modernIcon}>📊</Text>
                    <Text style={styles.modernPostsCount}>{item.posts_collected}개 분석</Text>
                  </View>
                </View>
              </TouchableOpacity>
            )}
            ListEmptyComponent={
              <View style={styles.modernEmptyContainer}>
                <Text style={styles.modernEmptyIcon}>📝</Text>
                <Text style={styles.modernEmptyText}>아직 생성된 보고서가 없어요</Text>
                <Text style={styles.modernEmptySubtext}>키워드를 입력하고 분석을 시작해보세요</Text>
              </View>
            }
          />
        )}

        {/* Report Detail Modal */}
        <Modal
          visible={reportModalVisible}
          animationType="slide"
          onRequestClose={() => setReportModalVisible(false)}
        >
          <SafeAreaView style={styles.modalContainer}>
            <View style={styles.modalHeader}>
              <TouchableOpacity
                onPress={() => setReportModalVisible(false)}
                style={styles.modalBackButton}
              >
                <Text style={styles.backButtonText}>‹ 닫기</Text>
              </TouchableOpacity>
              {selectedReport && (
                <View style={styles.modalTitleContainer}>
                  <Text style={styles.modalTitle}>{selectedReport.query_text}</Text>
                  <Text style={styles.modalDate}>
                    {formatDate(selectedReport.created_at)}
                  </Text>
                </View>
              )}
            </View>
            {selectedReport && (
              <ReportRenderer
                fullReport={selectedReport.full_report}
                reportLinks={reportLinks}
              />
            )}
          </SafeAreaView>
        </Modal>

      </SafeAreaView>
    );
  }

  const handleAnalyze = async () => {
    if (!keyword.trim()) {
      Alert.alert('알림', '키워드를 입력해주세요.');
      return;
    }
    
    const requestData = {
      query: keyword.trim(),
      sources: ['reddit'],
      user_nickname: savedNickname,
      length: reportLength,
      schedule_yn: 'N'
    };
    
    const requestUrl = `${API_BASE_URL}/api/v1/search`;
    
    // API 상태 표시
    logService.addLog(`${requestUrl} 분석 요청 중...`, 'info');
    logService.addLog(`키워드: ${keyword.trim()}`, 'info');
    logService.addLog(`보고서 길이: ${reportLength}`, 'info');
    
    logService.info('키워드 분석 시작', { 
      keyword: keyword.trim(), 
      length: reportLength,
      savedNickname,
      url: requestUrl,
      requestData
    });
    
    try {
      console.log('=== 실제 요청 URL ===');
      console.log(requestUrl);
      console.log('==================');
      logService.info('서버에 요청 전송 중...', { url: requestUrl });
      
      const response = await fetch(requestUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData),
      });

      logService.info('서버 응답 수신', { 
        status: response.status,
        statusText: response.statusText,
        headers: response.headers,
        ok: response.ok
      });

      if (response.ok) {
        const data = await response.json();
        logService.info('분석 요청 성공', { sessionId: data.session_id, responseData: data });
        logService.addLog(`분석 요청 성공! 세션ID: ${data.session_id}`, 'success');
        
        // 분석 요청 완료 메시지 표시
        Alert.alert(
          '분석 요청 완료', 
          '분석 요청이 완료되었습니다.\n분석에는 약 5분정도의 시간이 소요됩니다.\n\n완료되면 보고서 탭에서 확인하실 수 있습니다.',
          [
            {
              text: '확인',
              onPress: () => {
                setKeyword(''); // 키워드 초기화
              }
            }
          ]
        );
      } else {
        const errorText = await response.text();
        logService.error('분석 요청 실패', { 
          status: response.status,
          statusText: response.statusText,
          errorText
        });
        logService.addLog(`분석 요청 실패: ${response.status} ${response.statusText}`, 'error');
        Alert.alert('오류', `분석 요청에 실패했습니다. (상태: ${response.status})`);
      }
    } catch (error: any) {
      logService.error('분석 요청 오류', { 
        error: error?.message || error,
        stack: error?.stack,
        url: requestUrl,
        requestData,
        errorType: error?.name,
        errorCode: error?.code
      });
      
      // 네트워크 디버깅을 위한 추가 정보
      console.error('=== 네트워크 오류 상세 정보 ===');
      console.error('URL:', requestUrl);
      console.error('Method: POST');
      console.error('Headers:', { 'Content-Type': 'application/json' });
      console.error('Body:', JSON.stringify(requestData, null, 2));
      console.error('Error:', error);
      console.error('Error Type:', error?.name);
      console.error('Error Code:', error?.code);
      console.error('=========================');
      
      let errorMessage = '서버 연결에 실패했습니다';
      if (error?.message?.includes('Network request failed')) {
        errorMessage = '네트워크 연결을 확인해주세요';
      } else if (error?.message?.includes('timeout')) {
        errorMessage = '요청 시간이 초과되었습니다';
      }
      
      Alert.alert('오류', `${errorMessage}\n\n상세: ${error?.message || '알 수 없는 오류'}`);
    }
  };


  // Main Screen
  return (
    <SafeAreaView style={[styles.container, styles.darkContainer]}>
      <StatusBar barStyle="light-content" backgroundColor="#000000" />
      <View style={styles.modernMainHeader}>
        <View style={styles.mainHeaderTop}>
          <Text style={styles.mainHeaderGreeting}>안녕하세요,</Text>
          <DropdownMenu
            trigger={
              <View style={styles.profileButton}>
                <Text style={styles.profileIcon}>👤</Text>
              </View>
            }
            items={[
              {
                label: '로그 보기',
                icon: '📋',
                onPress: () => {
                  logService.info('로그 뷰어 열기');
                  setLogViewerVisible(true);
                }
              },
              {
                label: '로그아웃',
                icon: '🚪',
                color: '#FF3B30',
                onPress: () => {
                  Alert.alert(
                    '로그아웃',
                    '정말 로그아웃 하시겠습니까?',
                    [
                      { text: '취소', style: 'cancel' },
                      {
                        text: '로그아웃',
                        onPress: async () => {
                          logService.info('로그아웃');
                          await AsyncStorage.removeItem('savedNickname');
                          setCurrentScreen('login');
                          setNickname('');
                          setSavedNickname('');
                          setKeyword('');
                        },
                        style: 'destructive'
                      }
                    ]
                  );
                }
              }
            ]}
          />
        </View>
        <Text style={styles.mainHeaderName}>{savedNickname}님</Text>
      </View>
      
      <ScrollView 
        style={styles.modernScrollContent} 
        contentContainerStyle={styles.modernScrollContentContainer}
        showsVerticalScrollIndicator={false}
      >
        {/* 키워드 분석 카드 */}
        <View style={styles.modernAnalysisCard}>
          <View style={styles.cardHeader}>
            <Text style={styles.cardIcon}>🔍</Text>
            <Text style={styles.cardTitle}>키워드 분석</Text>
          </View>
          <Text style={styles.cardDescription}>
            관심 키워드를 입력하면 AI가 커뮤니티를 분석해드려요
          </Text>
          
          <View style={styles.modernInputWrapper}>
            <TextInput
              style={styles.modernMainInput}
              placeholder="예: 테슬라의 미래"
              placeholderTextColor="#666"
              value={keyword}
              onChangeText={setKeyword}
            />
          </View>
          
          <View style={styles.modernLengthSelector}>
            <Text style={styles.modernLengthLabel}>보고서 상세도</Text>
            <View style={styles.modernLengthButtons}>
              <TouchableOpacity
                style={[styles.modernLengthButton, reportLength === 'simple' && styles.modernLengthButtonActive, { marginRight: 4 }]}
                onPress={() => setReportLength('simple')}
              >
                <Text style={[styles.modernLengthButtonText, reportLength === 'simple' && styles.modernLengthButtonTextActive]}>간단</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.modernLengthButton, reportLength === 'moderate' && styles.modernLengthButtonActive, { marginHorizontal: 4 }]}
                onPress={() => setReportLength('moderate')}
              >
                <Text style={[styles.modernLengthButtonText, reportLength === 'moderate' && styles.modernLengthButtonTextActive]}>보통</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.modernLengthButton, reportLength === 'detailed' && styles.modernLengthButtonActive, { marginLeft: 4 }]}
                onPress={() => setReportLength('detailed')}
              >
                <Text style={[styles.modernLengthButtonText, reportLength === 'detailed' && styles.modernLengthButtonTextActive]}>상세</Text>
              </TouchableOpacity>
            </View>
          </View>
          
          <TouchableOpacity
            style={[styles.modernAnalyzeButton, !keyword.trim() && styles.modernButtonDisabled]}
            onPress={handleAnalyze}
            disabled={!keyword.trim()}
            activeOpacity={0.7}
          >
            <Text style={styles.modernAnalyzeButtonText}>분석 시작</Text>
          </TouchableOpacity>
        </View>
        
        {/* 메뉴 카드들 */}
        <TouchableOpacity
          style={styles.modernMenuCard}
          onPress={() => {
            setCurrentScreen('reports');
            fetchReports();
          }}
          activeOpacity={0.7}
        >
          <View style={styles.menuCardContent}>
            <View>
              <Text style={styles.menuCardIcon}>📄</Text>
              <Text style={styles.menuCardTitle}>보고서 목록</Text>
              <Text style={styles.menuCardSubtitle}>생성된 분석 보고서를 확인하세요</Text>
            </View>
            <Text style={styles.menuCardArrow}>→</Text>
          </View>
        </TouchableOpacity>
      </ScrollView>
      
      <LogViewer 
        visible={logViewerVisible}
        onClose={() => setLogViewerVisible(false)}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
  apiStatusBar: {
    height: 24,
    backgroundColor: '#007AFF',
    overflow: 'hidden',
    justifyContent: 'center',
  },
  apiStatusTextContainer: {
    flexDirection: 'row',
  },
  apiStatusText: {
    color: '#FFFFFF',
    fontSize: 11,
    fontWeight: '600',
    paddingHorizontal: 16,
    lineHeight: 24,
  },
  darkContainer: {
    backgroundColor: '#000000',
  },
  splashContainer: {
    backgroundColor: '#000000',
    justifyContent: 'center',
    alignItems: 'center',
  },
  content: {
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: 24,
  },
  logoContainer: {
    alignItems: 'center',
    marginBottom: 80,
  },
  iconContainer: {
    width: 100,
    height: 100,
    borderRadius: 25,
    backgroundColor: '#1A1A1A',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 24,
    borderWidth: 1,
    borderColor: '#333',
  },
  iconText: {
    fontSize: 50,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#1C1C1E',
    textAlign: 'center',
    marginBottom: 8,
  },
  splashTitle: {
    fontSize: 36,
    fontWeight: '700',
    color: '#FFFFFF',
    textAlign: 'center',
    marginBottom: 8,
    letterSpacing: -1,
  },
  subtitle: {
    fontSize: 16,
    color: '#666666',
    textAlign: 'center',
    marginBottom: 48,
  },
  splashSubtitle: {
    fontSize: 16,
    color: '#888',
    textAlign: 'center',
  },
  splashLoadingContainer: {
    position: 'absolute',
    bottom: 100,
    alignItems: 'center',
  },
  loadingContainer: {
    position: 'absolute',
    bottom: 100,
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    color: '#8E8E93',
  },
  inputContainer: {
    marginBottom: 16,
  },
  input: {
    height: 50,
    borderWidth: 1,
    borderColor: '#E5E5EA',
    borderRadius: 8,
    paddingHorizontal: 16,
    fontSize: 16,
    backgroundColor: '#F9F9F9',
    color: '#000',
  },
  button: {
    height: 50,
    backgroundColor: '#007AFF',
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  buttonDisabled: {
    backgroundColor: '#C7C7CC',
  },
  buttonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
  info: {
    fontSize: 14,
    color: '#8E8E93',
    textAlign: 'center',
  },
  registerButton: {
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#007AFF',
  },
  registerButtonText: {
    color: '#007AFF',
  },
  header: {
    backgroundColor: '#007AFF',
    padding: 20,
    paddingTop: 40,
  },
  headerTitle: {
    color: '#FFFFFF',
    fontSize: 20,
    fontWeight: 'bold',
    textAlign: 'center',
  },
  headerSubtitle: {
    color: '#FFFFFF',
    fontSize: 14,
    textAlign: 'center',
    marginTop: 4,
  },
  mainContent: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  welcomeText: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 16,
  },
  infoText: {
    fontSize: 16,
    color: '#666666',
    textAlign: 'center',
    marginBottom: 32,
  },
  logoutButton: {
    paddingHorizontal: 32,
    paddingVertical: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#007AFF',
  },
  logoutButtonText: {
    color: '#007AFF',
    fontSize: 16,
    fontWeight: '600',
  },
  menuButton: {
    paddingHorizontal: 32,
    paddingVertical: 16,
    backgroundColor: '#007AFF',
    borderRadius: 8,
    marginBottom: 16,
  },
  menuButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
  backButton: {
    marginBottom: 12,
  },
  backButtonText: {
    fontSize: 17,
    color: '#007AFF',
  },
  listContent: {
    padding: 16,
  },
  reportCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  reportHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  queryText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1C1C1E',
    flex: 1,
    marginRight: 8,
  },
  reportLength: {
    fontSize: 12,
    color: '#007AFF',
    backgroundColor: '#E3F2FD',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
    overflow: 'hidden',
  },
  summaryText: {
    fontSize: 14,
    color: '#3C3C43',
    lineHeight: 20,
    marginBottom: 12,
  },
  reportFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  dateText: {
    fontSize: 12,
    color: '#8E8E93',
  },
  postsCount: {
    fontSize: 12,
    color: '#8E8E93',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 60,
  },
  emptyText: {
    fontSize: 16,
    color: '#3C3C43',
  },
  modalContainer: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
  modalHeader: {
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E5EA',
  },
  modalBackButton: {
    marginBottom: 8,
  },
  modalTitleContainer: {
    marginLeft: 8,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#1C1C1E',
    marginBottom: 4,
  },
  modalDate: {
    fontSize: 14,
    color: '#8E8E93',
  },
  errorText: {
    color: '#FF3B30',
    fontSize: 12,
    marginTop: 4,
    marginLeft: 4,
  },
  checkButton: {
    backgroundColor: '#34C759',
    marginBottom: 8,
  },
  scrollContent: {
    flex: 1,
  },
  scrollContentContainer: {
    paddingBottom: 40,
  },
  analysisSection: {
    padding: 20,
    backgroundColor: '#F2F2F7',
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#1C1C1E',
    marginBottom: 8,
  },
  sectionDescription: {
    fontSize: 14,
    color: '#8E8E93',
    marginBottom: 20,
  },
  lengthSelector: {
    marginBottom: 20,
  },
  lengthLabel: {
    fontSize: 16,
    color: '#1C1C1E',
    marginBottom: 10,
  },
  lengthButtons: {
    flexDirection: 'row',
    gap: 10,
  },
  lengthButton: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#C7C7CC',
    alignItems: 'center',
  },
  lengthButtonActive: {
    backgroundColor: '#007AFF',
    borderColor: '#007AFF',
  },
  lengthButtonText: {
    fontSize: 14,
    color: '#8E8E93',
    fontWeight: '600',
  },
  lengthButtonTextActive: {
    color: '#FFFFFF',
  },
  analyzeButton: {
    height: 50,
    backgroundColor: '#007AFF',
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
  },
  menuSection: {
    padding: 20,
  },
  
  // Login Screen Styles
  loginHeader: {
    alignItems: 'center',
    marginBottom: 48,
  },
  loginLogo: {
    fontSize: 60,
    marginBottom: 16,
  },
  loginTitle: {
    fontSize: 32,
    fontWeight: '700',
    color: '#FFFFFF',
    letterSpacing: -1,
    marginBottom: 8,
  },
  loginSubtitle: {
    fontSize: 16,
    color: '#888',
  },
  loginForm: {
    width: '100%',
  },
  modernInputContainer: {
    marginBottom: 16,
  },
  inputLabel: {
    fontSize: 14,
    color: '#888',
    marginBottom: 8,
  },
  modernInput: {
    height: 56,
    backgroundColor: '#1A1A1A',
    borderRadius: 12,
    paddingHorizontal: 20,
    fontSize: 16,
    color: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#333',
  },
  checkboxContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 24,
  },
  checkbox: {
    width: 20,
    height: 20,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: '#666',
    marginRight: 8,
    justifyContent: 'center',
    alignItems: 'center',
  },
  checkboxChecked: {
    backgroundColor: '#4A90E2',
    borderColor: '#4A90E2',
  },
  checkmark: {
    color: '#FFFFFF',
    fontSize: 14,
  },
  checkboxLabel: {
    color: '#888',
    fontSize: 14,
  },
  modernButton: {
    height: 56,
    backgroundColor: '#4A90E2',
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  modernButtonDisabled: {
    backgroundColor: '#333',
  },
  modernButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
  textButton: {
    alignItems: 'center',
    paddingVertical: 12,
  },
  textButtonText: {
    color: '#888',
    fontSize: 14,
  },
  textButtonBold: {
    color: '#4A90E2',
    fontWeight: '600',
  },
  
  // Main Screen Styles
  modernMainHeader: {
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 16,
  },
  mainHeaderTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  mainHeaderGreeting: {
    fontSize: 14,
    color: '#888',
  },
  mainHeaderName: {
    fontSize: 24,
    fontWeight: '700',
    color: '#FFFFFF',
    letterSpacing: -0.5,
  },
  profileButton: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#1A1A1A',
    justifyContent: 'center',
    alignItems: 'center',
  },
  profileIcon: {
    fontSize: 16,
  },
  modernScrollContent: {
    flex: 1,
  },
  modernScrollContentContainer: {
    paddingHorizontal: 20,
    paddingBottom: 40,
  },
  modernAnalysisCard: {
    backgroundColor: '#1A1A1A',
    borderRadius: 16,
    padding: 24,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#333',
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  cardIcon: {
    fontSize: 24,
    marginRight: 8,
  },
  cardTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  cardDescription: {
    fontSize: 14,
    color: '#888',
    marginBottom: 20,
    lineHeight: 20,
  },
  modernInputWrapper: {
    marginBottom: 16,
  },
  modernMainInput: {
    height: 56,
    backgroundColor: '#000',
    borderRadius: 12,
    paddingHorizontal: 20,
    fontSize: 16,
    color: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#333',
  },
  modernLengthSelector: {
    marginBottom: 20,
  },
  modernLengthLabel: {
    fontSize: 14,
    color: '#888',
    marginBottom: 12,
  },
  modernLengthButtons: {
    flexDirection: 'row',
  },
  modernLengthButton: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 8,
    backgroundColor: '#000',
    borderWidth: 1,
    borderColor: '#333',
    alignItems: 'center',
  },
  modernLengthButtonActive: {
    backgroundColor: '#4A90E2',
    borderColor: '#4A90E2',
  },
  modernLengthButtonText: {
    fontSize: 14,
    color: '#666',
    fontWeight: '500',
  },
  modernLengthButtonTextActive: {
    color: '#FFFFFF',
  },
  modernAnalyzeButton: {
    height: 56,
    backgroundColor: '#4A90E2',
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  modernAnalyzeButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
  modernMenuCard: {
    backgroundColor: '#1A1A1A',
    borderRadius: 16,
    padding: 20,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#333',
  },
  menuCardContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  menuCardIcon: {
    fontSize: 32,
    marginBottom: 8,
  },
  menuCardTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#FFFFFF',
    marginBottom: 4,
  },
  menuCardSubtitle: {
    fontSize: 14,
    color: '#888',
  },
  menuCardArrow: {
    fontSize: 24,
    color: '#666',
  },
  
  // Reports Screen Styles
  modernHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#1A1A1A',
  },
  modernBackButton: {
    width: 40,
    height: 40,
    justifyContent: 'center',
    alignItems: 'center',
  },
  modernBackButtonText: {
    fontSize: 24,
    color: '#FFFFFF',
  },
  modernHeaderTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  centerLoadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  modernLoadingText: {
    marginTop: 12,
    fontSize: 14,
    color: '#888',
  },
  modernListContent: {
    padding: 20,
  },
  modernReportCard: {
    backgroundColor: '#1A1A1A',
    borderRadius: 16,
    padding: 20,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#333',
  },
  modernReportHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  modernQueryText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#FFFFFF',
    flex: 1,
    marginRight: 8,
  },
  modernBadge: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 6,
  },
  simpleBadge: {
    backgroundColor: '#4A90E2',
  },
  moderateBadge: {
    backgroundColor: '#7B68EE',
  },
  detailedBadge: {
    backgroundColor: '#FF6B6B',
  },
  modernBadgeText: {
    fontSize: 12,
    color: '#FFFFFF',
    fontWeight: '500',
  },
  modernSummaryText: {
    fontSize: 14,
    color: '#AAA',
    lineHeight: 20,
    marginBottom: 16,
  },
  modernReportFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  modernReportMeta: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  modernIcon: {
    fontSize: 14,
    marginRight: 4,
  },
  modernDateText: {
    fontSize: 12,
    color: '#666',
  },
  modernPostsCount: {
    fontSize: 12,
    color: '#666',
  },
  modernEmptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 100,
  },
  modernEmptyIcon: {
    fontSize: 48,
    marginBottom: 16,
  },
  modernEmptyText: {
    fontSize: 16,
    color: '#FFFFFF',
    marginBottom: 8,
  },
  modernEmptySubtext: {
    fontSize: 14,
    color: '#666',
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 30,
  },
  errorIcon: {
    fontSize: 60,
    marginBottom: 20,
  },
  errorTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#FFFFFF',
    marginBottom: 15,
  },
  errorMessage: {
    fontSize: 16,
    color: '#CCCCCC',
    textAlign: 'center',
    marginBottom: 30,
    lineHeight: 24,
  },
  retryButton: {
    backgroundColor: '#007AFF',
    paddingHorizontal: 30,
    paddingVertical: 15,
    borderRadius: 25,
  },
  retryButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
});

export default App;