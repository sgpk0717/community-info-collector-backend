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
  Modal,
  FlatList,
  Linking,
} from 'react-native';

const API_BASE_URL = 'https://community-info-collector-backend.onrender.com';

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
  const [currentScreen, setCurrentScreen] = React.useState<'splash' | 'login' | 'main' | 'reports'>('splash');
  const [nickname, setNickname] = React.useState('');
  const [savedNickname, setSavedNickname] = React.useState('');
  const [isLoading, setIsLoading] = React.useState(false);
  const [reports, setReports] = React.useState<Report[]>([]);
  const [selectedReport, setSelectedReport] = React.useState<Report | null>(null);
  const [reportLinks, setReportLinks] = React.useState<ReportLink[]>([]);
  const [reportModalVisible, setReportModalVisible] = React.useState(false);
  const [footnoteModalVisible, setFootnoteModalVisible] = React.useState(false);
  const [selectedFootnote, setSelectedFootnote] = React.useState<ReportLink | null>(null);
  
  // Splash animation
  const fadeAnim = React.useRef(new Animated.Value(0)).current;
  const scaleAnim = React.useRef(new Animated.Value(0.8)).current;

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

    // Show splash for 2 seconds
    setTimeout(() => {
      setCurrentScreen('login');
    }, 2000);
  }, []);

  const handleLogin = async () => {
    if (!nickname.trim()) {
      Alert.alert('알림', '닉네임을 입력해주세요.');
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/users/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ user_nickname: nickname.trim() }),
      });

      if (response.ok) {
        setSavedNickname(nickname.trim());
        setCurrentScreen('main');
      } else if (response.status === 404) {
        Alert.alert('로그인 실패', '등록되지 않은 닉네임입니다.\n회원가입이 필요합니다.');
      } else {
        Alert.alert('오류', '로그인에 실패했습니다. 다시 시도해주세요.');
      }
    } catch (error) {
      Alert.alert('오류', '서버 연결에 실패했습니다.');
      console.error('Login error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchReports = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/reports/${savedNickname}`);
      if (response.ok) {
        const data = await response.json();
        setReports(data.reports || []);
      }
    } catch (error) {
      console.error('Error fetching reports:', error);
      Alert.alert('오류', '보고서를 불러오는데 실패했습니다.');
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

  const handleFootnotePress = (footnoteNumber: number) => {
    const footnote = reportLinks.find(link => link.footnote_number === footnoteNumber);
    if (footnote) {
      setSelectedFootnote(footnote);
      setFootnoteModalVisible(true);
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

  // Splash Screen
  if (currentScreen === 'splash') {
    return (
      <View style={styles.container}>
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
            <Text style={styles.iconText}>🔍</Text>
          </View>
          <Text style={styles.title}>커뮤니티 정보 수집기</Text>
          <Text style={styles.subtitle}>Community Info Collector</Text>
        </Animated.View>
        
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#007AFF" />
          <Text style={styles.loadingText}>로딩 중...</Text>
        </View>
      </View>
    );
  }

  // Login Screen
  if (currentScreen === 'login') {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.content}>
          <Text style={styles.title}>Community Info{'\n'}Collector</Text>
          <Text style={styles.subtitle}>커뮤니티 정보 수집기 v2.0</Text>
          
          <View style={styles.inputContainer}>
            <TextInput
              style={styles.input}
              placeholder="닉네임을 입력하세요"
              placeholderTextColor="#999"
              value={nickname}
              onChangeText={setNickname}
              autoCapitalize="none"
              autoCorrect={false}
              editable={!isLoading}
            />
          </View>
          
          <TouchableOpacity
            style={[styles.button, isLoading && styles.buttonDisabled]}
            onPress={handleLogin}
            disabled={isLoading}
          >
            <Text style={styles.buttonText}>
              {isLoading ? '로그인 중...' : '로그인'}
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.button, styles.registerButton]}
            onPress={() => Alert.alert('알림', '회원가입 기능은 준비 중입니다.')}
            disabled={isLoading}
          >
            <Text style={[styles.buttonText, styles.registerButtonText]}>
              회원가입
            </Text>
          </TouchableOpacity>
          
          <Text style={styles.info}>
            닉네임만으로 간단하게 시작할 수 있습니다
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  // Reports Screen
  if (currentScreen === 'reports') {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.header}>
          <TouchableOpacity
            onPress={() => setCurrentScreen('main')}
            style={styles.backButton}
          >
            <Text style={styles.backButtonText}>‹ 뒤로</Text>
          </TouchableOpacity>
          <Text style={styles.headerTitle}>보고서 목록</Text>
        </View>

        {isLoading ? (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color="#007AFF" />
            <Text style={styles.loadingText}>보고서 불러오는 중...</Text>
          </View>
        ) : (
          <FlatList
            data={reports}
            keyExtractor={(item) => item.id}
            contentContainerStyle={styles.listContent}
            renderItem={({ item }) => (
              <TouchableOpacity
                style={styles.reportCard}
                onPress={() => handleReportPress(item)}
              >
                <View style={styles.reportHeader}>
                  <Text style={styles.queryText} numberOfLines={1}>
                    {item.query_text}
                  </Text>
                  <Text style={styles.reportLength}>{item.report_length}</Text>
                </View>

                <Text style={styles.summaryText} numberOfLines={3}>
                  {item.summary}
                </Text>

                <View style={styles.reportFooter}>
                  <Text style={styles.dateText}>{formatDate(item.created_at)}</Text>
                  <Text style={styles.postsCount}>{item.posts_collected}개 게시물</Text>
                </View>
              </TouchableOpacity>
            )}
            ListEmptyComponent={
              <View style={styles.emptyContainer}>
                <Text style={styles.emptyText}>아직 생성된 보고서가 없습니다.</Text>
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
              <ScrollView style={styles.reportContent}>
                <Text style={styles.reportText}>
                  {selectedReport.full_report.split(/\[(\d+)\]/).map((part, index) => {
                    if (index % 2 === 1) {
                      const footnoteNum = parseInt(part);
                      return (
                        <Text
                          key={index}
                          style={styles.footnoteText}
                          onPress={() => handleFootnotePress(footnoteNum)}
                        >
                          [{part}]
                        </Text>
                      );
                    }
                    return <Text key={index}>{part}</Text>;
                  })}
                </Text>
              </ScrollView>
            )}
          </SafeAreaView>
        </Modal>

        {/* Footnote Modal */}
        <Modal
          visible={footnoteModalVisible}
          animationType="slide"
          transparent={true}
          onRequestClose={() => setFootnoteModalVisible(false)}
        >
          <View style={styles.footnoteModalOverlay}>
            <View style={styles.footnoteModalContent}>
              {selectedFootnote && (
                <>
                  <View style={styles.footnoteModalHeader}>
                    <Text style={styles.footnoteModalTitle}>
                      참조 [{selectedFootnote.footnote_number}]
                    </Text>
                    <TouchableOpacity
                      onPress={() => setFootnoteModalVisible(false)}
                      style={styles.closeButton}
                    >
                      <Text style={styles.closeButtonText}>✕</Text>
                    </TouchableOpacity>
                  </View>

                  <ScrollView style={styles.footnoteModalBody}>
                    <Text style={styles.postTitle}>{selectedFootnote.title}</Text>
                    
                    <View style={styles.postMeta}>
                      <Text style={styles.metaText}>
                        r/{selectedFootnote.subreddit} • u/{selectedFootnote.author}
                      </Text>
                      <Text style={styles.metaText}>
                        {formatDate(selectedFootnote.created_utc)}
                      </Text>
                    </View>

                    <View style={styles.postStats}>
                      <View style={styles.statItem}>
                        <Text style={styles.statValue}>{selectedFootnote.score}</Text>
                        <Text style={styles.statLabel}>점수</Text>
                      </View>
                      <View style={styles.statItem}>
                        <Text style={styles.statValue}>{selectedFootnote.comments}</Text>
                        <Text style={styles.statLabel}>댓글</Text>
                      </View>
                    </View>

                    <TouchableOpacity
                      style={styles.openLinkButton}
                      onPress={() => {
                        if (selectedFootnote.url) {
                          Linking.openURL(selectedFootnote.url);
                        }
                      }}
                    >
                      <Text style={styles.openLinkButtonText}>원본 게시물 보기</Text>
                    </TouchableOpacity>
                  </ScrollView>
                </>
              )}
            </View>
          </View>
        </Modal>
      </SafeAreaView>
    );
  }

  // Main Screen
  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>커뮤니티 정보 수집기</Text>
        <Text style={styles.headerSubtitle}>안녕하세요, {savedNickname}님!</Text>
      </View>
      
      <View style={styles.mainContent}>
        <Text style={styles.welcomeText}>환영합니다!</Text>
        <Text style={styles.infoText}>
          이제 키워드를 입력하여 커뮤니티 정보를 수집할 수 있습니다.
        </Text>
        
        <TouchableOpacity
          style={styles.menuButton}
          onPress={() => {
            setCurrentScreen('reports');
            fetchReports();
          }}
        >
          <Text style={styles.menuButtonText}>📄 보고서 목록 보기</Text>
        </TouchableOpacity>
        
        <TouchableOpacity
          style={styles.logoutButton}
          onPress={() => {
            setCurrentScreen('login');
            setNickname('');
          }}
        >
          <Text style={styles.logoutButtonText}>로그아웃</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFFFFF',
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
    backgroundColor: '#007AFF',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 8,
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
  subtitle: {
    fontSize: 16,
    color: '#666666',
    textAlign: 'center',
    marginBottom: 48,
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
  reportContent: {
    padding: 20,
  },
  reportText: {
    fontSize: 15,
    lineHeight: 22,
    color: '#3C3C43',
  },
  footnoteText: {
    color: '#007AFF',
    fontWeight: '600',
    textDecorationLine: 'underline',
  },
  footnoteModalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'flex-end',
  },
  footnoteModalContent: {
    backgroundColor: '#FFFFFF',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: '70%',
    paddingBottom: 34,
  },
  footnoteModalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E5EA',
  },
  footnoteModalTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#1C1C1E',
  },
  closeButton: {
    padding: 8,
  },
  closeButtonText: {
    fontSize: 24,
    color: '#8E8E93',
  },
  footnoteModalBody: {
    padding: 20,
  },
  postTitle: {
    fontSize: 17,
    fontWeight: '600',
    color: '#1C1C1E',
    marginBottom: 12,
    lineHeight: 22,
  },
  postMeta: {
    marginBottom: 16,
  },
  metaText: {
    fontSize: 13,
    color: '#8E8E93',
    marginBottom: 4,
  },
  postStats: {
    flexDirection: 'row',
    marginBottom: 20,
    paddingVertical: 16,
    backgroundColor: '#F2F2F7',
    borderRadius: 12,
  },
  statItem: {
    flex: 1,
    alignItems: 'center',
  },
  statValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#1C1C1E',
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 13,
    color: '#8E8E93',
  },
  openLinkButton: {
    backgroundColor: '#007AFF',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
  },
  openLinkButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
});

export default App;