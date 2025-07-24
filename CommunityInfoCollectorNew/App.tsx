import React, { useState, useEffect } from 'react';
import {
  SafeAreaView,
  StatusBar,
  StyleSheet,
  View,
  Text,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { logService } from './src/services/log.service';

// Import screens
import LoginScreen from './src/screens/LoginScreen';
import RegisterScreen from './src/screens/RegisterScreen';
import HomeScreen from './src/screens/HomeScreen';
import ReportsScreen from './src/screens/ReportsScreen';

// API base URL
const API_BASE_URL = 'https://community-info-collector-backend.onrender.com';

// Types
type AuthStackParamList = {
  Login: undefined;
  Register: undefined;
};

type MainTabParamList = {
  Home: undefined;
  Reports: undefined;
};

const Tab = createBottomTabNavigator<MainTabParamList>();

function App(): JSX.Element {
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userNickname, setUserNickname] = useState('');
  const [currentScreen, setCurrentScreen] = useState<'login' | 'register' | 'main'>('login');

  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      const savedNickname = await AsyncStorage.getItem('savedNickname');
      if (savedNickname) {
        setUserNickname(savedNickname);
        setIsAuthenticated(true);
        setCurrentScreen('main');
        logService.info('자동 로그인 성공', { nickname: savedNickname });
      }
    } catch (error) {
      logService.error('인증 상태 확인 실패', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogin = async (nickname: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/users/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ user_nickname: nickname.trim() }),
      });

      if (response.ok) {
        await AsyncStorage.setItem('savedNickname', nickname.trim());
        setUserNickname(nickname.trim());
        setIsAuthenticated(true);
        setCurrentScreen('main');
        logService.info('로그인 성공', { nickname: nickname.trim() });
      } else if (response.status === 404) {
        Alert.alert(
          '로그인 실패',
          '등록되지 않은 닉네임입니다.\n닉네임을 등록해주세요.',
          [
            { text: '취소', style: 'cancel' },
            { text: '닉네임 등록', onPress: () => setCurrentScreen('register') }
          ]
        );
      } else {
        Alert.alert('오류', '로그인에 실패했습니다.');
      }
    } catch (error) {
      logService.error('로그인 오류', error);
      Alert.alert('오류', '서버 연결에 실패했습니다.');
    }
  };

  const handleRegister = async (nickname: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/users/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ user_nickname: nickname.trim() }),
      });

      if (response.ok) {
        Alert.alert(
          '등록 완료',
          '닉네임 등록이 완료되었습니다.',
          [
            {
              text: '확인',
              onPress: () => {
                setCurrentScreen('login');
              }
            }
          ]
        );
      } else {
        const data = await response.json();
        Alert.alert('오류', data.detail || '닉네임 등록에 실패했습니다.');
      }
    } catch (error) {
      logService.error('등록 오류', error);
      Alert.alert('오류', '서버 연결에 실패했습니다.');
    }
  };

  const handleLogout = async () => {
    await AsyncStorage.removeItem('savedNickname');
    setIsAuthenticated(false);
    setUserNickname('');
    setCurrentScreen('login');
    logService.info('로그아웃');
  };

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
      </View>
    );
  }

  if (!isAuthenticated) {
    if (currentScreen === 'register') {
      return (
        <RegisterScreen
          onRegister={handleRegister}
          onBack={() => setCurrentScreen('login')}
        />
      );
    }
    return (
      <LoginScreen
        onLogin={handleLogin}
        onRegister={() => setCurrentScreen('register')}
      />
    );
  }

  return (
    <NavigationContainer>
      <StatusBar barStyle="light-content" backgroundColor="#000000" />
      <Tab.Navigator
        screenOptions={{
          tabBarStyle: {
            backgroundColor: '#000000',
            borderTopColor: '#333333',
            height: 60,
            paddingBottom: 8,
          },
          tabBarActiveTintColor: '#007AFF',
          tabBarInactiveTintColor: '#8E8E93',
          headerStyle: {
            backgroundColor: '#000000',
          },
          headerTintColor: '#FFFFFF',
          headerTitleAlign: 'left',
        }}
      >
        <Tab.Screen
          name="Home"
          options={{
            title: '실시간 분석',
            tabBarIcon: ({ color, size }) => (
              <View style={styles.tabIconContainer}>
                <Text style={[styles.tabIcon, { color }]}>🔍</Text>
              </View>
            ),
            headerTitle: () => (
              <View style={styles.headerContainer}>
                <Text style={styles.greeting}>안녕하세요,</Text>
                <Text style={styles.nickname}>{userNickname}님</Text>
              </View>
            ),
            headerRight: () => (
              <View style={styles.profileButton}>
                <Text style={styles.profileIcon}>👤</Text>
              </View>
            ),
          }}
        >
          {() => <HomeScreen userNickname={userNickname} apiBaseUrl={API_BASE_URL} />}
        </Tab.Screen>
        <Tab.Screen
          name="Reports"
          options={{
            title: '보고서',
            tabBarIcon: ({ color, size }) => (
              <View style={styles.tabIconContainer}>
                <Text style={[styles.tabIcon, { color }]}>📋</Text>
              </View>
            ),
            headerTitle: '보고서',
          }}
        >
          {() => <ReportsScreen userNickname={userNickname} apiBaseUrl={API_BASE_URL} />}
        </Tab.Screen>
      </Tab.Navigator>
    </NavigationContainer>
  );
}

const styles = StyleSheet.create({
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#000000',
  },
  headerContainer: {
    marginLeft: 16,
  },
  greeting: {
    fontSize: 14,
    color: '#8E8E93',
  },
  nickname: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#FFFFFF',
    marginTop: 2,
  },
  profileButton: {
    marginRight: 16,
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#1C1C1E',
    justifyContent: 'center',
    alignItems: 'center',
  },
  profileIcon: {
    fontSize: 20,
  },
  tabIconContainer: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  tabIcon: {
    fontSize: 24,
  },
});

export default App;