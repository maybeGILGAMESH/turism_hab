import React, { useState, useEffect } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Text, StatusBar, Platform } from 'react-native';
import NetInfo from '@react-native-community/netinfo';

import CameraScreen from './screens/CameraScreen';
import HistoryScreen from './screens/HistoryScreen';
import QueueScreen from './screens/QueueScreen';
import SettingsScreen from './screens/SettingsScreen';
import ExploreScreen from './screens/ExploreScreen';
import { RequestQueue } from './services/RequestQueue';
import { StorageService } from './services/StorageService';

const Tab = createBottomTabNavigator();

const DEFAULT_API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL ||
  (Platform.OS === 'android' ? 'http://10.0.2.2:8000' : 'http://localhost:8000');

export default function App() {
  const [isConnected, setIsConnected] = useState(true);
  const [queueCount, setQueueCount] = useState(0);
  const [apiUrl, setApiUrl] = useState(DEFAULT_API_BASE_URL);

  useEffect(() => {
    // Загружаем URL из настроек при старте
    const loadApiUrl = async () => {
      try {
        const settings = await StorageService.getSettings();
        const url = settings.serverUrl || DEFAULT_API_BASE_URL;
        console.log('🔧 Loading API URL from settings:', url);
        
        // Предупреждение о неправильном порте
        try {
          const urlObj = new URL(url);
          if (urlObj.port === '8501') {
            console.error('⚠️ ВНИМАНИЕ: Используется порт 8501 (Streamlit) вместо 8000 (FastAPI)!');
            console.error('   Измените URL в настройках на:', `http://${urlObj.hostname}:8000`);
          }
        } catch (e) {
          // Не критично, если URL не парсится
        }
        
        setApiUrl(url);
        console.log('✅ API URL loaded:', url);
      } catch (error) {
        console.error('❌ Error loading API URL:', error);
        console.log('   Using default URL:', DEFAULT_API_BASE_URL);
        setApiUrl(DEFAULT_API_BASE_URL);
      }
    };
    loadApiUrl();
  }, []);

  useEffect(() => {
    // Проверка подключения к интернету
    const unsubscribe = NetInfo.addEventListener(async state => {
      setIsConnected(state.isConnected);
      if (state.isConnected) {
        // Когда появляется интернет, обрабатываем очередь
        try {
          const settings = await StorageService.getSettings();
          const currentApiUrl = settings.serverUrl || DEFAULT_API_BASE_URL;
          console.log('🌐 Internet connection restored, processing queue with URL:', currentApiUrl);
          await RequestQueue.processQueue(currentApiUrl);
        } catch (error) {
          console.error('❌ Error processing queue in App.js:', error);
          console.error('   Error details:', {
            message: error.message,
            name: error.name,
          });
        }
      }
    });

    // Загружаем количество запросов в очереди
    loadQueueCount();

    return () => unsubscribe();
  }, []);

  const loadQueueCount = async () => {
    const count = await RequestQueue.getQueueLength();
    setQueueCount(count);
  };

  return (
    <NavigationContainer>
      <StatusBar barStyle="dark-content" />
      <Tab.Navigator
        screenOptions={{
          tabBarActiveTintColor: '#0369a1',
          tabBarInactiveTintColor: '#666',
          headerStyle: {
            backgroundColor: '#075985',
          },
          headerTintColor: '#fff',
          headerTitleStyle: {
            fontWeight: 'bold',
          },
        }}
      >
        <Tab.Screen
          name="Camera"
          options={{
            title: 'Распознавание',
            tabBarIcon: ({ color }) => <Text style={{ fontSize: 24 }}>📸</Text>,
          }}
        >
          {props => (
            <CameraScreen
              {...props}
              isConnected={isConnected}
              apiUrl={apiUrl}
              onQueueUpdate={loadQueueCount}
            />
          )}
        </Tab.Screen>
        <Tab.Screen
          name="Explore"
          options={{ title: 'Места', tabBarIcon: () => <Text style={{ fontSize: 24 }}>🗺️</Text> }}
        >
          {props => <ExploreScreen {...props} apiUrl={apiUrl} />}
        </Tab.Screen>
        <Tab.Screen
          name="History"
          options={{
            title: 'История',
            tabBarIcon: ({ color }) => <Text style={{ fontSize: 24 }}>📚</Text>,
            tabBarBadge: queueCount > 0 ? queueCount : null,
          }}
        >
          {props => <HistoryScreen {...props} />}
        </Tab.Screen>
        <Tab.Screen
          name="Queue"
          options={{
            title: 'Очередь',
            tabBarIcon: ({ color }) => <Text style={{ fontSize: 24 }}>⏳</Text>,
            tabBarBadge: queueCount > 0 ? queueCount : null,
          }}
        >
          {props => (
            <QueueScreen
              {...props}
              isConnected={isConnected}
              apiUrl={apiUrl}
              onQueueUpdate={loadQueueCount}
            />
          )}
        </Tab.Screen>
        <Tab.Screen
          name="Settings"
          options={{
            title: 'Настройки',
            tabBarIcon: ({ color }) => <Text style={{ fontSize: 24 }}>⚙️</Text>,
          }}
        >
          {props => <SettingsScreen {...props} apiUrl={apiUrl} onSettingsChange={setApiUrl} />}
        </Tab.Screen>
      </Tab.Navigator>
    </NavigationContainer>
  );
}
