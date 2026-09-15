import React, { useCallback, useState } from 'react';
import { Alert, FlatList, Image, RefreshControl, StyleSheet, Text, View } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { Button, Card, Chip, EmptyState, IconButton } from '../components/ui';
import { StorageService } from '../services/StorageService';
import { colors, spacing, type } from '../theme';

export default function HistoryScreen({ navigation }) {
  const [history, setHistory] = useState([]);
  const [refreshing, setRefreshing] = useState(false);

  const loadHistory = useCallback(async () => {
    setHistory(await StorageService.getHistory());
  }, []);

  useFocusEffect(useCallback(() => { loadHistory(); }, [loadHistory]));

  const onRefresh = async () => {
    setRefreshing(true);
    await loadHistory();
    setRefreshing(false);
  };

  const deleteItem = itemId => {
    Alert.alert('Удаление', 'Удалить эту запись?', [
      { text: 'Отмена', style: 'cancel' },
      { text: 'Удалить', style: 'destructive', onPress: async () => { await StorageService.deleteFromHistory(itemId); loadHistory(); } },
    ]);
  };

  const clearHistory = () => {
    Alert.alert('Очистка истории', 'Удалить всю историю распознаваний?', [
      { text: 'Отмена', style: 'cancel' },
      { text: 'Очистить', style: 'destructive', onPress: async () => { await StorageService.clearHistory(); loadHistory(); } },
    ]);
  };

  const renderItem = ({ item }) => {
    const place = item.object;
    const recognized = item.success || item.recognized;
    return (
      <Card
        style={styles.item}
        onPress={place ? () => navigation.navigate('PlaceDetail', { id: place.id, name: place.name }) : undefined}
        accessibilityLabel={place ? `${place.name}, открыть карточку` : undefined}
      >
        {item.imageUri ? <Image source={{ uri: item.imageUri }} style={styles.thumb} /> : <View style={[styles.thumb, styles.thumbEmpty]} />}
        <View style={styles.body}>
          {recognized ? (
            <>
              <Chip icon="check-circle-outline" tone="ok" label={`Уверенность ${(item.confidence * 100).toFixed(0)}%`} />
              <Text style={type.h3} numberOfLines={2}>{place ? place.name : `Объект #${item.object_id}`}</Text>
            </>
          ) : (
            <>
              <Chip icon="help-circle-outline" tone="gold" label="Не распознано" />
              <Text style={type.small} numberOfLines={2}>{item.message || 'Попробуйте другой ракурс'}</Text>
            </>
          )}
          <Text style={type.small}>{new Date(item.timestamp).toLocaleString('ru-RU')}</Text>
        </View>
        <IconButton icon="delete-outline" label="Удалить запись" color={colors.muted} onPress={() => deleteItem(item.id)} />
      </Card>
    );
  };

  return (
    <View style={styles.container}>
      <FlatList
        data={history}
        renderItem={renderItem}
        keyExtractor={item => item.id}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        contentContainerStyle={[styles.list, !history.length && styles.flexGrow]}
        ListHeaderComponent={history.length ? (
          <View style={styles.header}>
            <Text style={type.label}>Записей: {history.length} · хранится только на устройстве</Text>
            <Button compact variant="danger" title="Очистить" icon="delete-sweep-outline" onPress={clearHistory} />
          </View>
        ) : null}
        ListEmptyComponent={
          <EmptyState icon="history" title="История пуста" text="Распознанные достопримечательности появятся здесь.">
            <Button compact title="Распознать место" icon="camera-outline" onPress={() => navigation.navigate('Camera')} />
          </EmptyState>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  list: { padding: spacing.lg, gap: spacing.sm },
  flexGrow: { flexGrow: 1, justifyContent: 'center' },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: spacing.sm, marginBottom: spacing.xs },
  item: { flexDirection: 'row', alignItems: 'center', padding: spacing.sm, gap: spacing.md, marginBottom: spacing.sm },
  thumb: { width: 72, height: 72, borderRadius: 10 },
  thumbEmpty: { backgroundColor: colors.sky },
  body: { flex: 1, gap: 4 },
});
