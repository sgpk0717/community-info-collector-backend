import React, { useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Animated,
} from 'react-native';

interface SecondSplashScreenProps {
  userNickname: string;
  onFinish: () => void;
}

export default function SecondSplashScreen({ userNickname, onFinish }: SecondSplashScreenProps) {
  const fadeAnim = new Animated.Value(0);
  const slideAnim = new Animated.Value(30);

  useEffect(() => {
    // 페이드인 + 슬라이드업 애니메이션
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 600,
        useNativeDriver: true,
      }),
      Animated.timing(slideAnim, {
        toValue: 0,
        duration: 600,
        useNativeDriver: true,
      }),
    ]).start();

    // 1.5초 후 종료
    const timer = setTimeout(() => {
      Animated.timing(fadeAnim, {
        toValue: 0,
        duration: 300,
        useNativeDriver: true,
      }).start(() => {
        onFinish();
      });
    }, 1500);

    return () => clearTimeout(timer);
  }, []);

  return (
    <View style={styles.container}>
      <Animated.View
        style={[
          styles.content,
          {
            opacity: fadeAnim,
            transform: [{ translateY: slideAnim }],
          },
        ]}
      >
        <Text style={styles.welcome}>환영합니다!</Text>
        <Text style={styles.nickname}>{userNickname}님</Text>
        <View style={styles.divider} />
        <Text style={styles.message}>오늘도 유익한 분석이 되길 바랍니다</Text>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000000',
    justifyContent: 'center',
    alignItems: 'center',
  },
  content: {
    alignItems: 'center',
  },
  welcome: {
    fontSize: 24,
    fontWeight: '600',
    color: '#8E8E93',
    marginBottom: 8,
  },
  nickname: {
    fontSize: 36,
    fontWeight: '700',
    color: '#FFFFFF',
    marginBottom: 24,
  },
  divider: {
    width: 60,
    height: 2,
    backgroundColor: '#007AFF',
    marginBottom: 24,
  },
  message: {
    fontSize: 16,
    color: '#8E8E93',
    fontWeight: '500',
  },
});