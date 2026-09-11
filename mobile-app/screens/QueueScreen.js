import React, { useState, useEffect } from 'react';
import { StorageService } from '../services/StorageService';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Alert,
  RefreshControl,
  ActivityIndicator,
} from 'react-native';
import { RequestQueue } from '../services/RequestQueue';
import NetInfo from '@react-native-community/netinfo';

export default function QueueScreen({ isConnected, apiUrl: defaultApiUrl, onQueueUpdate }) {
  const [queue, setQueue] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [apiUrl, setApiUrl] = useState(defaultApiUrl);

  useEffect(() => {
    loadQueue();
    // Загружаем сохраненный URL сервера из настроек
    const loadApiUrl = async () => {
      try {
        const settings = await StorageService.getSettings();
        if (settings.serverUrl) {
          setApiUrl(settings.serverUrl);
        }
      } catch (error) {
        console.error('Error loading API URL:', error);
      }
    };
    loadApiUrl();
  }, []);

  const loadQueue = async () => {
    try {
      const q = await RequestQueue.getQueue();
      setQueue(q);
    } catch (error) {
      console.error('Error loading queue:', error);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadQueue();
    setRefreshing(false);
  };

  const processQueue = async () => {
    const isConnectedNow = await NetInfo.fetch().then(state => state.isConnected);
    if (!isConnectedNow) {
      Alert.alert('Ошибка', 'Нет подключения к интернету');
      return;
    }

    setProcessing(true);
    try {
      await RequestQueue.processQueue(apiUrl);
      await loadQueue();
      onQueueUpdate();
      Alert.alert('Успех', 'Очередь обработана');
    } catch (error) {
      console.error('Error processing queue:', error);
      Alert.alert('Ошибка', 'Не удалось обработать очередь');
    } finally {
      setProcessing(false);
    }
  };

  const clearQueue = () => {
    Alert.alert(
      'Очистка очереди',
      'Вы уверены, что хотите очистить всю очередь?',
      [
        { text: 'Отмена', style: 'cancel' },
        {
          text: 'Очистить',
          style: 'destructive',
          onPress: async () => {
            await RequestQueue.clearQueue();
            loadQueue();
            onQueueUpdate();
          },
        },
      ]
    );
  };

  const removeItem = async (itemId) => {
    Alert.alert(
      'Удаление',
      'Вы уверены, что хотите удалить этот запрос из очереди?',
      [
        { text: 'Отмена', style: 'cancel' },
        {
          text: 'Удалить',
          style: 'destructive',
          onPress: async () => {
            await RequestQueue.removeFromQueue(itemId);
            loadQueue();
            onQueueUpdate();
          },
        },
      ]
    );
  };

  const renderItem = ({ item }) => (
    <View style={styles.item}>
      <View style={styles.itemContent}>
        <Text style={styles.itemType}>
          {item.type === 'recognize' ? '🔍 Распознавание' : item.type}
        </Text>
        <Text style={styles.itemDate}>
          {new Date(item.createdAt).toLocaleString('ru-RU')}
        </Text>
        <Text style={styles.itemRetries}>
          Попыток: {item.retries}/3
        </Text>
      </View>
      <TouchableOpacity
        style={styles.deleteButton}
        onPress={() => removeItem(item.id)}
      >
        <Text style={styles.deleteButtonText}>🗑️</Text>
      </TouchableOpacity>
    </View>
  );

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>⏳ Очередь запросов</Text>
        <Text style={styles.subtitle}>
          {isConnected ? '✅ Подключено к интернету' : '⚠️ Офлайн режим'}
        </Text>
        {queue.length > 0 && (
          <View style={styles.buttonContainer}>
            {isConnected && (
              <TouchableOpacity
                style={[styles.processButton, processing && styles.buttonDisabled]}
                onPress={processQueue}
                disabled={processing}
              >
                {processing ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <Text style={styles.buttonText}>Обработать очередь</Text>
                )}
              </TouchableOpacity>
            )}
            <TouchableOpacity style={styles.clearButton} onPress={clearQueue}>
              <Text style={styles.clearButtonText}>Очистить очередь</Text>
            </TouchableOpacity>
          </View>
        )}
      </View>

      {queue.length === 0 ? (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyText}>Очередь пуста</Text>
          <Text style={styles.emptySubtext}>
            Запросы, созданные в офлайн режиме, будут отображаться здесь
          </Text>
        </View>
      ) : (
        <FlatList
          data={queue}
          renderItem={renderItem}
          keyExtractor={item => item.id}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
          }
          contentContainerStyle={styles.list}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    backgroundColor: '#075985',
    padding: 20,
    paddingTop: 40,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 5,
  },
  subtitle: {
    fontSize: 16,
    color: '#fff',
    marginBottom: 10,
  },
  buttonContainer: {
    flexDirection: 'row',
    marginTop: 10,
  },
  processButton: {
    backgroundColor: '#27ae60',
    padding: 10,
    borderRadius: 5,
    marginRight: 10,
    flex: 1,
    alignItems: 'center',
  },
  clearButton: {
    backgroundColor: '#e74c3c',
    padding: 10,
    borderRadius: 5,
    flex: 1,
    alignItems: 'center',
  },
  buttonText: {
    color: '#fff',
    fontWeight: 'bold',
  },
  clearButtonText: {
    color: '#fff',
    fontWeight: 'bold',
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  list: {
    padding: 10,
  },
  item: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    marginBottom: 10,
    borderRadius: 10,
    padding: 15,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  itemContent: {
    flex: 1,
  },
  itemType: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#2c3e50',
    marginBottom: 5,
  },
  itemDate: {
    fontSize: 12,
    color: '#999',
    marginBottom: 5,
  },
  itemRetries: {
    fontSize: 12,
    color: '#666',
  },
  deleteButton: {
    padding: 5,
    justifyContent: 'center',
  },
  deleteButtonText: {
    fontSize: 20,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  emptyText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#999',
    marginBottom: 10,
  },
  emptySubtext: {
    fontSize: 14,
    color: '#999',
    textAlign: 'center',
  },
});
