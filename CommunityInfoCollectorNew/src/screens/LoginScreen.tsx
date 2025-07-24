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
} from 'react-native';

interface LoginScreenProps {
  onLogin: (nickname: string) => void;
  onRegister: () => void;
}

export default function LoginScreen({ onLogin, onRegister }: LoginScreenProps) {
  const [nickname, setNickname] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async () => {
    if (!nickname.trim()) return;
    
    setIsLoading(true);
    await onLogin(nickname);
    setIsLoading(false);
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#000000" />
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
          <View style={styles.inputContainer}>
            <TextInput
              style={styles.input}
              placeholder="닉네임을 입력하세요"
              placeholderTextColor="#666666"
              value={nickname}
              onChangeText={setNickname}
              autoCapitalize="none"
              returnKeyType="done"
              onSubmitEditing={handleLogin}
              editable={!isLoading}
            />
          </View>

          <TouchableOpacity
            style={[styles.loginButton, !nickname.trim() && styles.loginButtonDisabled]}
            onPress={handleLogin}
            disabled={!nickname.trim() || isLoading}
            activeOpacity={0.7}
          >
            {isLoading ? (
              <ActivityIndicator color="#FFFFFF" />
            ) : (
              <Text style={styles.loginButtonText}>로그인</Text>
            )}
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.registerButton}
            onPress={onRegister}
            disabled={isLoading}
          >
            <Text style={styles.registerButtonText}>
              처음이신가요? <Text style={styles.registerButtonBold}>닉네임 등록하기</Text>
            </Text>
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
    justifyContent: 'center',
    paddingHorizontal: 24,
  },
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
    fontWeight: 'bold',
    color: '#FFFFFF',
    marginBottom: 8,
  },
  loginSubtitle: {
    fontSize: 16,
    color: '#8E8E93',
  },
  loginForm: {
    width: '100%',
  },
  inputContainer: {
    backgroundColor: '#1C1C1E',
    borderRadius: 12,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#333333',
  },
  input: {
    fontSize: 16,
    color: '#FFFFFF',
    paddingVertical: 16,
    paddingHorizontal: 16,
  },
  loginButton: {
    backgroundColor: '#007AFF',
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
    marginBottom: 16,
  },
  loginButtonDisabled: {
    opacity: 0.5,
  },
  loginButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
  registerButton: {
    alignItems: 'center',
    paddingVertical: 16,
  },
  registerButtonText: {
    color: '#8E8E93',
    fontSize: 14,
  },
  registerButtonBold: {
    color: '#007AFF',
    fontWeight: '600',
  },
});