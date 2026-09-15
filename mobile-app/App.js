import 'react-native-gesture-handler';
import React, { useCallback, useEffect, useState } from 'react';
import { DefaultTheme, NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createStackNavigator } from '@react-navigation/stack';
import { Pressable, StatusBar, StyleSheet, Text } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import NetInfo from '@react-native-community/netinfo';

import CameraScreen from './screens/CameraScreen';
import ExploreScreen from './screens/ExploreScreen';
import GuideScreen from './screens/GuideScreen';
import HistoryScreen from './screens/HistoryScreen';
import PlaceDetailScreen from './screens/PlaceDetailScreen';
import QueueScreen from './screens/QueueScreen';
import RouteScreen from './screens/RouteScreen';
import SettingsScreen from './screens/SettingsScreen';
import { Icon } from './components/ui';
import { DEFAULT_API_BASE_URL } from './config';
import { AppStateProvider } from './context/AppState';
import { RequestQueue } from './services/RequestQueue';
import { StorageService } from './services/StorageService';
import { colors } from './theme';

const Tab = createBottomTabNavigator();
const Stack = createStackNavigator();

const navigationTheme = {
  ...DefaultTheme,
  colors: { ...DefaultTheme.colors, primary: colors.amur, background: colors.bg, card: colors.white, text: colors.ink, border: colors.line },
};

const headerOptions = {
  headerStyle: { backgroundColor: colors.amur },
  headerTintColor: colors.white,
  headerTitleStyle: { fontWeight: '700', fontSize: 17 },
};

function GuideHeaderButton({ navigation }) {
  return (
    <Pressable
      onPress={() => navigation.navigate('Guide')}
      accessibilityRole="button"
      accessibilityLabel="Открыть ИИ-гида"
      style={({ pressed }) => [styles.guideButton, pressed && { opacity: 0.85 }]}
    >
      <Icon name="robot-happy-outline" color={colors.white} size={20} />
      <Text style={styles.guideButtonText}>Гид</Text>
    </Pressable>
  );
}

function MainTabs({ isConnected, queueCount, loadQueueCount, apiUrl, setApiUrl }) {
  return (
    <Tab.Navigator
      screenOptions={({ navigation }) => ({
        ...headerOptions,
        headerRight: () => <GuideHeaderButton navigation={navigation} />,
        tabBarActiveTintColor: colors.amur,
        tabBarInactiveTintColor: colors.muted,
        tabBarLabelStyle: { fontSize: 11, fontWeight: '600' },
        tabBarStyle: { borderTopColor: colors.line, backgroundColor: colors.white },
      })}
    >
      <Tab.Screen
        name="Camera"
        options={{ title: 'Распознавание', tabBarIcon: ({ color, size }) => <Icon name="camera-outline" color={color} size={size} /> }}
      >
        {props => <CameraScreen {...props} isConnected={isConnected} apiUrl={apiUrl} onQueueUpdate={loadQueueCount} />}
      </Tab.Screen>
      <Tab.Screen
        name="Explore"
        component={ExploreScreen}
        options={{ title: 'Места', tabBarIcon: ({ color, size }) => <Icon name="map-search-outline" color={color} size={size} /> }}
      />
      <Tab.Screen
        name="History"
        component={HistoryScreen}
        options={{ title: 'История', tabBarIcon: ({ color, size }) => <Icon name="history" color={color} size={size} /> }}
      />
      <Tab.Screen
        name="Queue"
        options={{
          title: 'Очередь',
          tabBarIcon: ({ color, size }) => <Icon name="tray-arrow-up" color={color} size={size} />,
          tabBarBadge: queueCount > 0 ? queueCount : undefined,
          tabBarBadgeStyle: { backgroundColor: colors.gold },
        }}
      >
        {props => <QueueScreen {...props} isConnected={isConnected} apiUrl={apiUrl} onQueueUpdate={loadQueueCount} />}
      </Tab.Screen>
      <Tab.Screen
        name="Settings"
        options={{ title: 'Настройки', tabBarIcon: ({ color, size }) => <Icon name="cog-outline" color={color} size={size} /> }}
      >
        {props => <SettingsScreen {...props} apiUrl={apiUrl} onSettingsChange={setApiUrl} />}
      </Tab.Screen>
    </Tab.Navigator>
  );
}

export default function App() {
  const [isConnected, setIsConnected] = useState(true);
  const [queueCount, setQueueCount] = useState(0);
  const [apiUrl, setApiUrl] = useState(DEFAULT_API_BASE_URL);

  const loadQueueCount = useCallback(async () => {
    setQueueCount(await RequestQueue.getQueueLength());
  }, []);

  useEffect(() => {
    StorageService.getSettings()
      .then(settings => setApiUrl(settings.serverUrl || DEFAULT_API_BASE_URL))
      .catch(() => setApiUrl(DEFAULT_API_BASE_URL));
  }, []);

  useEffect(() => {
    const unsubscribe = NetInfo.addEventListener(async state => {
      setIsConnected(state.isConnected);
      if (state.isConnected) {
        try {
          const settings = await StorageService.getSettings();
          await RequestQueue.processQueue(settings.serverUrl || DEFAULT_API_BASE_URL);
          loadQueueCount();
        } catch (error) {
          console.error('Error processing queue:', error.message);
        }
      }
    });
    loadQueueCount();
    return () => unsubscribe();
  }, [loadQueueCount]);

  return (
    <SafeAreaProvider>
      <AppStateProvider apiUrl={apiUrl}>
        <NavigationContainer theme={navigationTheme}>
          <StatusBar barStyle="light-content" backgroundColor={colors.amurDark} />
          <Stack.Navigator screenOptions={{ ...headerOptions, headerBackTitle: 'Назад', cardStyle: { backgroundColor: colors.bg } }}>
            <Stack.Screen name="Main" options={{ headerShown: false }}>
              {props => (
                <MainTabs
                  {...props}
                  isConnected={isConnected}
                  queueCount={queueCount}
                  loadQueueCount={loadQueueCount}
                  apiUrl={apiUrl}
                  setApiUrl={setApiUrl}
                />
              )}
            </Stack.Screen>
            <Stack.Screen name="PlaceDetail" component={PlaceDetailScreen} options={({ route }) => ({ title: route.params?.name || 'Место' })} />
            <Stack.Screen name="Route" component={RouteScreen} options={{ title: 'Маршрут' }} />
            <Stack.Screen name="Guide" component={GuideScreen} options={{ title: 'ИИ-гид' }} />
          </Stack.Navigator>
        </NavigationContainer>
      </AppStateProvider>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  guideButton: {
    minHeight: 40,
    minWidth: 44,
    marginRight: 10,
    paddingHorizontal: 12,
    borderRadius: 20,
    backgroundColor: colors.gold,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 4,
  },
  guideButtonText: { color: colors.white, fontWeight: '700', fontSize: 14 },
});
