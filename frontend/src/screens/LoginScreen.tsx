import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/AppNavigator';
import { STORAGE_KEYS } from '../constants/config';
import api from '../services/api';

type LoginScreenNavigationProp = NativeStackNavigationProp<RootStackParamList, 'Login'>;

export default function LoginScreen() {
  const navigation = useNavigation<LoginScreenNavigationProp>();
  const [nickname, setNickname] = useState('');
  const [loading, setLoading] = useState(false);
  const [savedNickname, setSavedNickname] = useState<string | null>(null);

  React.useEffect(() => {
    loadSavedNickname();
  }, []);

  const loadSavedNickname = async () => {
    try {
      const saved = await AsyncStorage.getItem(STORAGE_KEYS.SAVED_NICKNAME);
      if (saved) {
        setSavedNickname(saved);
        setNickname(saved);
      }
    } catch (error) {
      console.error('Failed to load saved nickname:', error);
    }
  };

  const handleLogin = async () => {
    if (!nickname.trim()) {
      Alert.alert('알림', '닉네임을 입력해주세요.');
      return;
    }

    setLoading(true);
    try {
      // 사용자 조회 (로그인)
      const response = await api.loginUser(nickname.trim());
      
      if (response.success) {
        // 로그인한 닉네임 저장 (세션)
        await AsyncStorage.setItem(STORAGE_KEYS.USER_NICKNAME, nickname.trim());
        // 닉네임 저장 (자동완성용)
        await AsyncStorage.setItem(STORAGE_KEYS.SAVED_NICKNAME, nickname.trim());
        
        // 메인 화면으로 이동
        navigation.reset({
          index: 0,
          routes: [{ name: 'Main' }],
        });
      } else {
        Alert.alert('로그인 실패', '등록되지 않은 닉네임입니다.\n회원가입을 먼저 진행해주세요.');
      }
    } catch (error) {
      Alert.alert('오류', '로그인에 실패했습니다. 다시 시도해주세요.');
      console.error('Login error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = () => {
    navigation.navigate('Register' as any);
  };

  return (
    <KeyboardAvoidingView 
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <View style={styles.content}>
        <Text style={styles.title}>Community Info{'\n'}Collector</Text>
        <Text style={styles.subtitle}>커뮤니티 정보 수집기 v2.0</Text>
        
        <View style={styles.inputContainer}>
          <TextInput
            style={styles.input}
            placeholder="닉네임을 입력하세요"
            value={nickname}
            onChangeText={setNickname}
            autoCapitalize="none"
            autoCorrect={false}
            editable={!loading}
          />
        </View>
        
        <TouchableOpacity
          style={[styles.button, loading && styles.buttonDisabled]}
          onPress={handleLogin}
          disabled={loading}
        >
          <Text style={styles.buttonText}>
            {loading ? '로그인 중...' : '로그인'}
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.button, styles.registerButton]}
          onPress={handleRegister}
          disabled={loading}
        >
          <Text style={[styles.buttonText, styles.registerButtonText]}>
            회원가입
          </Text>
        </TouchableOpacity>
        
        <Text style={styles.info}>
          {savedNickname 
            ? `최근 로그인: ${savedNickname}` 
            : '닉네임만으로 간단하게 시작할 수 있습니다'}
        </Text>
      </View>
    </KeyboardAvoidingView>
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
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#000000',
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: '#666666',
    textAlign: 'center',
    marginBottom: 48,
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
});