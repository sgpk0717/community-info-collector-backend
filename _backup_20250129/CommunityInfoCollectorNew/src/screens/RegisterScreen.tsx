import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  SafeAreaView,
  StatusBar,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  Alert,
} from 'react-native';

interface RegisterScreenProps {
  onRegister: (nickname: string) => void;
  onBack: () => void;
}

export default function RegisterScreen({ onRegister, onBack }: RegisterScreenProps) {
  const [nickname, setNickname] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [nicknameError, setNicknameError] = useState('');

  const checkNicknameAvailability = async () => {
    if (!nickname.trim()) {
      setNicknameError('닉네임을 입력해주세요.');
      return;
    }

    if (nickname.trim().length < 2) {
      setNicknameError('닉네임은 2자 이상이어야 합니다.');
      return;
    }

    setIsLoading(true);
    setNicknameError('');

    try {
      const response = await fetch(
        `https://community-info-collector-backend.onrender.com/api/v1/users/check-nickname?nickname=${encodeURIComponent(nickname.trim())}`
      );
      const data = await response.json();

      if (data.is_available) {
        setNicknameError('');
        Alert.alert('확인', '사용 가능한 닉네임입니다.');
      } else {
        setNicknameError('이미 사용 중인 닉네임입니다.');
      }
    } catch (error) {
      setNicknameError('닉네임 확인 중 오류가 발생했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegister = async () => {
    if (!nickname.trim() || nicknameError) return;
    
    setIsLoading(true);
    await onRegister(nickname);
    setIsLoading(false);
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#000000" />
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.content}
      >
        <View style={styles.header}>
          <TouchableOpacity onPress={onBack} style={styles.backButton}>
            <Text style={styles.backButtonText}>← 뒤로</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.registerHeader}>
          <Text style={styles.registerLogo}>👤</Text>
          <Text style={styles.registerTitle}>닉네임 등록</Text>
          <Text style={styles.registerSubtitle}>사용하실 닉네임을 입력해주세요</Text>
        </View>

        <View style={styles.registerForm}>
          <View style={styles.inputContainer}>
            <TextInput
              style={styles.input}
              placeholder="닉네임 (2자 이상)"
              placeholderTextColor="#666666"
              value={nickname}
              onChangeText={(text) => {
                setNickname(text);
                setNicknameError('');
              }}
              autoCapitalize="none"
              editable={!isLoading}
            />
          </View>
          
          {nicknameError ? (
            <Text style={styles.errorText}>{nicknameError}</Text>
          ) : null}

          <TouchableOpacity
            style={[styles.checkButton, !nickname.trim() && styles.checkButtonDisabled]}
            onPress={checkNicknameAvailability}
            disabled={!nickname.trim() || isLoading}
          >
            <Text style={styles.checkButtonText}>중복 확인</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.registerButton, (!nickname.trim() || !!nicknameError) && styles.registerButtonDisabled]}
            onPress={handleRegister}
            disabled={!nickname.trim() || !!nicknameError || isLoading}
            activeOpacity={0.7}
          >
            {isLoading ? (
              <ActivityIndicator color="#FFFFFF" />
            ) : (
              <Text style={styles.registerButtonText}>등록하기</Text>
            )}
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000000',
  },
  content: {
    flex: 1,
    paddingHorizontal: 24,
  },
  header: {
    paddingTop: 16,
    paddingBottom: 24,
  },
  backButton: {
    paddingVertical: 8,
  },
  backButtonText: {
    color: '#007AFF',
    fontSize: 16,
  },
  registerHeader: {
    alignItems: 'center',
    marginBottom: 48,
  },
  registerLogo: {
    fontSize: 60,
    marginBottom: 16,
  },
  registerTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#FFFFFF',
    marginBottom: 8,
  },
  registerSubtitle: {
    fontSize: 16,
    color: '#8E8E93',
    textAlign: 'center',
  },
  registerForm: {
    width: '100%',
  },
  inputContainer: {
    backgroundColor: '#1C1C1E',
    borderRadius: 12,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: '#333333',
  },
  input: {
    fontSize: 16,
    color: '#FFFFFF',
    paddingVertical: 16,
    paddingHorizontal: 16,
  },
  errorText: {
    color: '#FF3B30',
    fontSize: 14,
    marginBottom: 16,
    marginLeft: 4,
  },
  checkButton: {
    backgroundColor: '#1C1C1E',
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
    marginBottom: 8,
    borderWidth: 1,
    borderColor: '#333333',
  },
  checkButtonDisabled: {
    opacity: 0.5,
  },
  checkButtonText: {
    color: '#007AFF',
    fontSize: 16,
    fontWeight: '600',
  },
  registerButton: {
    backgroundColor: '#007AFF',
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
    marginTop: 8,
  },
  registerButtonDisabled: {
    opacity: 0.5,
  },
  registerButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
});