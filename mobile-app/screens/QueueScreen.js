import React, { useCallback, useEffect, useState } from 'react';
import { Alert, FlatList, RefreshControl, StyleSheet, Text, View } from 'react-native';
import NetInfo from '@react-native-community/netinfo';
import { useFocusEffect } from '@react-navigation/native';
import { Button, Card, EmptyState, Icon, IconButton, Notice } from '../components/ui';
import { RequestQueue } from '../services/RequestQueue';
import { StorageService } from '../services/StorageService';
import { colors, spacing, type } from '../theme';

export default function QueueScreen({ isConnected, apiUrl: defaultApiUrl, onQueueUpdate }) {
  const [queue, setQueue] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [apiUrl, setApiUrl] = useState(defaultApiUrl);

  const loadQueue = useCallback(async () => {
    setQueue(await RequestQueue.getQueue());
  }, []);

  useEffect(() => {
    StorageService.getSettings().then(settings => setApiUrl(settings.serverUrl || defaultApiUrl));
  }, [defaultApiUrl]);

  useFocusEffect(useCallback(() => { loadQueue(); }, [loadQueue]));

  const onRefresh = async () => {
    setRefreshing(true);
    await loadQueue();
    setRefreshing(false);
  };

  const processQueue = async () => {
    const online = await NetInfo.fetch().then(state => state.isConnected);
    if (!online) {
      Alert.alert('Нет сети', 'Очередь обработается, когда появится подключение.');
      return;
    }
    setProcessing(true);
    try {
      await RequestQueue.processQueue(apiUrl);
      await loadQueue();
      onQueueUpdate();
      Alert.alert('Готово', 'Очередь обработана');
    } catch (error) {
      Alert.alert('Ошибка', 'Не удалось обработать очередь');
    } finally {
      setProcessing(false);
    }
  };

  const clearQueue = () => {
    Alert.alert('Очистка очереди', 'Удалить все отложенные запросы?', [
      { text: 'Отмена', style: 'cancel' },
      { text: 'Очистить', style: 'destructive', onPress: async () => { await RequestQueue.clearQueue(); loadQueue(); onQueueUpdate(); } },
    ]);
  };

  const removeItem = itemId => {
    Alert.alert('Удаление', 'Удалить этот запрос из очереди?', [
      { text: 'Отмена', style: 'cancel' },
      { text: 'Удалить', style: 'destructive', onPress: async () => { await RequestQueue.removeFromQueue(itemId); loadQueue(); onQueueUpdate(); } },
    ]);
  };

  return (
    <View style={styles.container}>
      <FlatList
        data={queue}
        keyExtractor={item => item.id}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        contentContainerStyle={[styles.list, !queue.length && styles.flexGrow]}
        ListHeaderComponent={
          <View style={styles.header}>
            <Notice tone={isConnected ? 'ok' : 'warn'} icon={isConnected ? 'wifi' : 'wifi-off'}>
              {isConnected ? 'Подключено — отложенные фото можно отправить сейчас.' : 'Офлайн-режим: новые фото будут ждать сети.'}
            </Notice>
            {queue.length ? (
              <View style={styles.row}>
                {isConnected ? <Button compact title="Отправить" icon="upload-outline" variant="success" onPress={processQueue} loading={processing} style={styles.flex} /> : null}
                <Button compact title="Очистить" icon="delete-sweep-outline" variant="danger" onPress={clearQueue} style={styles.flex} />
              </View>
            ) : null}
          </View>
        }
        ListEmptyComponent={<EmptyState icon="tray-arrow-up" title="Очередь пуста" text="Фото, сделанные без сети, будут ждать отправки здесь." />}
        renderItem={({ item }) => (
          <Card style={styles.item}>
            <View style={styles.iconWrap}><Icon name="image-search-outline" size={22} color={colors.amur} /></View>
            <View style={styles.flex}>
              <Text style={type.h3}>{item.type === 'recognize' ? 'Распознавание фото' : item.type}</Text>
              <Text style={type.small}>{new Date(item.createdAt).toLocaleString('ru-RU')} · попыток {item.retries}/3</Text>
            </View>
            <IconButton icon="delete-outline" label="Удалить из очереди" color={colors.muted} onPress={() => removeItem(item.id)} />
          </Card>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  list: { padding: spacing.lg, gap: spacing.sm },
  flexGrow: { flexGrow: 1 },
  header: { gap: spacing.sm, marginBottom: spacing.sm },
  row: { flexDirection: 'row', gap: spacing.sm },
  flex: { flex: 1 },
  item: { flexDirection: 'row', alignItems: 'center', gap: spacing.md, padding: spacing.md, marginBottom: spacing.sm },
  iconWrap: { width: 40, height: 40, borderRadius: 20, backgroundColor: colors.sky, alignItems: 'center', justifyContent: 'center' },
});
