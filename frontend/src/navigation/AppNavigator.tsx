import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { STORAGE_KEYS } from '../constants/config';

// Screen imports
import HomeScreen from '../screens/HomeScreen';
import SearchScreen from '../screens/SearchScreen';
import ReportsScreen from '../screens/ReportsScreen';
import ScheduleScreen from '../screens/ScheduleScreen';
import SettingsScreen from '../screens/SettingsScreen';
import LoginScreen from '../screens/LoginScreen';
import RegisterScreen from '../screens/RegisterScreen';
import ReportDetailScreen from '../screens/ReportDetailScreen';
import SplashScreen from '../screens/SplashScreen';

export type RootStackParamList = {
  Login: undefined;
  Register: undefined;
  Main: undefined;
  ReportDetail: { reportId: string };
};

export type MainTabParamList = {
  Home: undefined;
  Search: undefined;
  Reports: undefined;
  Schedule: undefined;
  Settings: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();
const Tab = createBottomTabNavigator<MainTabParamList>();

function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={{
        tabBarActiveTintColor: '#007AFF',
        tabBarInactiveTintColor: '#8E8E93',
        tabBarStyle: {
          backgroundColor: '#FFFFFF',
          borderTopWidth: 1,
          borderTopColor: '#E5E5EA',
        },
      }}
    >
      <Tab.Screen 
        name="Home" 
        component={HomeScreen}
        options={{
          title: '홈',
          headerShown: false,
        }}
      />
      <Tab.Screen 
        name="Search" 
        component={SearchScreen}
        options={{
          title: '검색',
          headerShown: false,
        }}
      />
      <Tab.Screen 
        name="Reports" 
        component={ReportsScreen}
        options={{
          title: '보고서',
          headerShown: false,
        }}
      />
      <Tab.Screen 
        name="Schedule" 
        component={ScheduleScreen}
        options={{
          title: '스케줄',
          headerShown: false,
        }}
      />
      <Tab.Screen 
        name="Settings" 
        component={SettingsScreen}
        options={{
          title: '설정',
          headerShown: false,
        }}
      />
    </Tab.Navigator>
  );
}

export default function AppNavigator() {
  const [isLoading, setIsLoading] = React.useState(true);
  const [userNickname, setUserNickname] = React.useState<string | null>(null);

  React.useEffect(() => {
    checkUser();
  }, []);

  const checkUser = async () => {
    try {
      const nickname = await AsyncStorage.getItem(STORAGE_KEYS.USER_NICKNAME);
      setUserNickname(nickname);
    } catch (error) {
      console.error('Failed to load user:', error);
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return <SplashScreen />;
  }

  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        {userNickname ? (
          <>
            <Stack.Screen name="Main" component={MainTabs} />
            <Stack.Screen 
              name="ReportDetail" 
              component={ReportDetailScreen}
              options={{ 
                headerShown: true,
                title: '보고서 상세',
                headerBackTitle: '뒤로',
              }}
            />
          </>
        ) : (
          <>
            <Stack.Screen name="Login" component={LoginScreen} />
            <Stack.Screen name="Register" component={RegisterScreen} />
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}