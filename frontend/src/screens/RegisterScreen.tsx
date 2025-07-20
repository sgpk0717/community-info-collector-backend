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
  ActivityIndicator,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/AppNavigator';
import { STORAGE_KEYS } from '../constants/config';
import api from '../services/api';

type RegisterScreenNavigationProp = NativeStackNavigationProp<RootStackParamList, 'Register'>;

export default function RegisterScreen() {
  const navigation = useNavigation<RegisterScreenNavigationProp>();
  const [nickname, setNickname] = useState('');
  const [checkStatus, setCheckStatus] = useState<'none' | 'checking' | 'available' | 'taken'>('none');
  const [loading, setLoading] = useState(false);

  const handleCheckNickname = async () => {
    if (!nickname.trim()) {
      Alert.alert('알림', '닉네임을 입력해주세요.');
      return;
    }

    if (nickname.trim().length < 2) {
      Alert.alert('알림', '닉네임은 2자 이상이어야 합니다.');
      return;
    }

    if (nickname.trim().length > 20) {
      Alert.alert('알림', '닉네임은 20자 이하여야 합니다.');
      return;
    }

    setCheckStatus('checking');
    try {
      const response = await api.checkNickname(nickname.trim());
      if (response.isAvailable) {
        setCheckStatus('available');
        Alert.alert('확인', '사용 가능한 닉네임입니다.');
      } else {
        setCheckStatus('taken');
        Alert.alert('알림', '이미 사용 중인 닉네임입니다.');
      }
    } catch (error) {
      setCheckStatus('none');
      Alert.alert('오류', '닉네임 확인에 실패했습니다.');
      console.error('Check nickname error:', error);
    }
  };

  const handleRegister = async () => {
    if (checkStatus !== 'available') {
      Alert.alert('알림', '닉네임 중복확인을 먼저 해주세요.');
      return;
    }

    setLoading(true);
    try {
      const response = await api.registerUser(nickname.trim());
      
      if (response.success) {
        // 로그인 상태로 만들기
        await AsyncStorage.setItem(STORAGE_KEYS.USER_NICKNAME, nickname.trim());
        // 닉네임 저장 (자동완성용)
        await AsyncStorage.setItem(STORAGE_KEYS.SAVED_NICKNAME, nickname.trim());
        
        Alert.alert(
          '회원가입 완료',
          '회원가입이 완료되었습니다.',
          [
            {
              text: '확인',
              onPress: () => {
                navigation.reset({
                  index: 0,
                  routes: [{ name: 'Main' }],
                });
              },
            },
          ],
        );
      } else {
        Alert.alert('오류', '회원가입에 실패했습니다.');
      }
    } catch (error) {
      Alert.alert('오류', '회원가입에 실패했습니다. 다시 시도해주세요.');
      console.error('Register error:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = () => {
    switch (checkStatus) {
      case 'available':
        return '#34C759';
      case 'taken':
        return '#FF3B30';
      default:
        return '#E5E5EA';
    }
  };

  const getStatusText = () => {
    switch (checkStatus) {
      case 'checking':
        return '확인 중...';
      case 'available':
        return '✓ 사용 가능';
      case 'taken':
        return '✗ 사용 불가';
      default:
        return '';
    }
  };

  return (
    <KeyboardAvoidingView 
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <View style={styles.header}>
        <TouchableOpacity
          style={styles.backButton}
          onPress={() => navigation.goBack()}
        >
          <Text style={styles.backButtonText}>← 뒤로</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.content}>
        <Text style={styles.title}>회원가입</Text>
        <Text style={styles.subtitle}>사용할 닉네임을 입력해주세요</Text>
        
        <View style={styles.inputContainer}>
          <View style={styles.inputWrapper}>
            <TextInput
              style={[
                styles.input,
                { borderColor: getStatusColor() }
              ]}
              placeholder="닉네임 (2-20자)"
              value={nickname}
              onChangeText={(text) => {
                setNickname(text);
                setCheckStatus('none');
              }}
              autoCapitalize="none"
              autoCorrect={false}
              editable={!loading}
            />
            <TouchableOpacity
              style={styles.checkButton}
              onPress={handleCheckNickname}
              disabled={loading || checkStatus === 'checking'}
            >
              {checkStatus === 'checking' ? (
                <ActivityIndicator size="small" color="#007AFF" />
              ) : (
                <Text style={styles.checkButtonText}>중복확인</Text>
              )}
            </TouchableOpacity>
          </View>
          {checkStatus !== 'none' && checkStatus !== 'checking' && (
            <Text style={[
              styles.statusText,
              { color: getStatusColor() }
            ]}>
              {getStatusText()}
            </Text>
          )}
        </View>

        <TouchableOpacity
          style={[
            styles.button,
            (loading || checkStatus !== 'available') && styles.buttonDisabled
          ]}
          onPress={handleRegister}
          disabled={loading || checkStatus !== 'available'}
        >
          <Text style={styles.buttonText}>
            {loading ? '가입 중...' : '가입하기'}
          </Text>
        </TouchableOpacity>

        <View style={styles.rules}>
          <Text style={styles.rulesTitle}>닉네임 규칙</Text>
          <Text style={styles.rulesText}>• 2자 이상 20자 이하</Text>
          <Text style={styles.rulesText}>• 특수문자 사용 가능</Text>
          <Text style={styles.rulesText}>• 중복 불가</Text>
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
  header: {
    paddingTop: Platform.OS === 'ios' ? 50 : 20,
    paddingHorizontal: 16,
    paddingBottom: 10,
  },
  backButton: {
    padding: 8,
  },
  backButtonText: {
    fontSize: 16,
    color: '#007AFF',
  },
  content: {
    flex: 1,
    paddingHorizontal: 24,
    paddingTop: 40,
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#000000',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: '#666666',
    marginBottom: 48,
  },
  inputContainer: {
    marginBottom: 24,
  },
  inputWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  input: {
    flex: 1,
    height: 50,
    borderWidth: 2,
    borderRadius: 8,
    paddingHorizontal: 16,
    fontSize: 16,
    backgroundColor: '#F9F9F9',
    marginRight: 8,
  },
  checkButton: {
    height: 50,
    paddingHorizontal: 20,
    backgroundColor: '#007AFF',
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    minWidth: 80,
  },
  checkButtonText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '600',
  },
  statusText: {
    marginTop: 8,
    fontSize: 14,
    fontWeight: '500',
  },
  button: {
    height: 50,
    backgroundColor: '#007AFF',
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 32,
  },
  buttonDisabled: {
    backgroundColor: '#C7C7CC',
  },
  buttonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
  rules: {
    backgroundColor: '#F9F9F9',
    padding: 16,
    borderRadius: 8,
  },
  rulesTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#666666',
    marginBottom: 8,
  },
  rulesText: {
    fontSize: 14,
    color: '#8E8E93',
    marginBottom: 4,
  },
});