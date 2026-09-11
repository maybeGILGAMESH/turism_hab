import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Image,
  Alert,
  RefreshControl,
} from 'react-native';
import { StorageService } from '../services/StorageService';

export default function HistoryScreen() {
  const [history, setHistory] = useState([]);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const h = await StorageService.getHistory();
      setHistory(h);
    } catch (error) {
      console.error('Error loading history:', error);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadHistory();
    setRefreshing(false);
  };

  const deleteItem = async (itemId) => {
    Alert.alert(
      'Удаление',
      'Вы уверены, что хотите удалить эту запись?',
      [
        { text: 'Отмена', style: 'cancel' },
        {
          text: 'Удалить',
          style: 'destructive',
          onPress: async () => {
            await StorageService.deleteFromHistory(itemId);
            loadHistory();
          },
        },
      ]
    );
  };

  const clearHistory = () => {
    Alert.alert(
      'Очистка истории',
      'Вы уверены, что хотите очистить всю историю?',
      [
        { text: 'Отмена', style: 'cancel' },
        {
          text: 'Очистить',
          style: 'destructive',
          onPress: async () => {
            await StorageService.clearHistory();
            loadHistory();
          },
        },
      ]
    );
  };

  const renderItem = ({ item }) => (
    <View style={styles.item}>
      {item.imageUri && (
        <Image source={{ uri: item.imageUri }} style={styles.itemImage} />
      )}
      <View style={styles.itemContent}>
        {item.success ? (
          <>
            <Text style={styles.itemTitle}>
              ✅ ID: {item.object_id}
            </Text>
            <Text style={styles.itemSubtitle}>
              Уверенность: {(item.confidence * 100).toFixed(1)}%
            </Text>
            {item.description && (
              <Text style={styles.itemDescription} numberOfLines={3}>
                {item.description}
              </Text>
            )}
          </>
        ) : (
          <>
            <Text style={styles.itemTitleError}>
              ⚠️ Не распознано
            </Text>
            <Text style={styles.itemDescription}>
              {item.message || 'Достопримечательность не найдена'}
            </Text>
          </>
        )}
        <Text style={styles.itemDate}>
          {new Date(item.timestamp).toLocaleString('ru-RU')}
        </Text>
      </View>
      <TouchableOpacity
        style={styles.deleteButton}
        onPress={() => deleteItem(item.id)}
      >
        <Text style={styles.deleteButtonText}>🗑️</Text>
      </TouchableOpacity>
    </View>
  );

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>📚 Личный кабинет</Text>
        <Text style={styles.subtitle}>История распознаваний</Text>
        {history.length > 0 && (
          <TouchableOpacity style={styles.clearButton} onPress={clearHistory}>
            <Text style={styles.clearButtonText}>Очистить историю</Text>
          </TouchableOpacity>
        )}
      </View>

      {history.length === 0 ? (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyText}>История пуста</Text>
          <Text style={styles.emptySubtext}>
            Распознанные достопримечательности будут отображаться здесь
          </Text>
        </View>
      ) : (
        <FlatList
          data={history}
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
  clearButton: {
    alignSelf: 'flex-end',
    padding: 8,
  },
  clearButtonText: {
    color: '#fff',
    fontSize: 14,
  },
  list: {
    padding: 10,
  },
  item: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    marginBottom: 10,
    borderRadius: 10,
    padding: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  itemImage: {
    width: 80,
    height: 80,
    borderRadius: 5,
    marginRight: 10,
  },
  itemContent: {
    flex: 1,
  },
  itemTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#27ae60',
    marginBottom: 5,
  },
  itemTitleError: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#e74c3c',
    marginBottom: 5,
  },
  itemSubtitle: {
    fontSize: 14,
    color: '#666',
    marginBottom: 5,
  },
  itemDescription: {
    fontSize: 12,
    color: '#999',
    marginTop: 5,
  },
  itemDate: {
    fontSize: 11,
    color: '#999',
    marginTop: 5,
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
