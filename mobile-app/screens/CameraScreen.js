import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Alert, Image, ScrollView, StyleSheet, Text, View } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import NetInfo from '@react-native-community/netinfo';
import { Button, Card, Chip, Icon, Notice } from '../components/ui';
import { useAppState } from '../context/AppState';
import { RequestQueue } from '../services/RequestQueue';
import { StorageService } from '../services/StorageService';
import { colors, radius, spacing, type } from '../theme';

export default function CameraScreen({ navigation, isConnected, apiUrl: defaultApiUrl, onQueueUpdate }) {
  const { routeIds, toggleRoute } = useAppState();
  const [image, setImage] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [apiUrl, setApiUrl] = useState(defaultApiUrl);

  useEffect(() => {
    StorageService.getSettings().then(settings => setApiUrl(settings.serverUrl || defaultApiUrl));
  }, [defaultApiUrl]);

  const choose = picked => {
    if (!picked.canceled) {
      setImage(picked.assets[0].uri);
      setResult(null);
    }
  };

  const pickImage = async () => {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Нет доступа', 'Разрешите доступ к галерее в настройках устройства.');
      return;
    }
    choose(await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], allowsEditing: true, aspect: [4, 3], quality: 0.8 }));
  };

  const takePhoto = async () => {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Нет доступа', 'Разрешите доступ к камере в настройках устройства.');
      return;
    }
    choose(await ImagePicker.launchCameraAsync({ allowsEditing: true, aspect: [4, 3], quality: 0.8 }));
  };

  const enqueue = async () => {
    await RequestQueue.addToQueue({ type: 'recognize', imageUri: image, data: {} });
    onQueueUpdate();
  };

  const recognizeImage = async () => {
    if (!image) return;
    setLoading(true);
    setResult(null);
    const online = await NetInfo.fetch().then(state => state.isConnected);
    if (!online) {
      try {
        await enqueue();
        Alert.alert('Офлайн-режим', 'Фото добавлено в очередь и будет распознано, когда появится сеть.');
      } catch (error) {
        Alert.alert('Ошибка', 'Не удалось добавить запрос в очередь');
      }
      setLoading(false);
      return;
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 60000);
    try {
      const formData = new FormData();
      if (image.startsWith('blob:') || image.startsWith('data:')) {
        const blob = await (await fetch(image)).blob();
        formData.append('file', blob, 'photo.jpg');
      } else {
        formData.append('file', { uri: image, type: 'image/jpeg', name: 'photo.jpg' });
      }
      const response = await fetch(`${apiUrl}/api/recognize`, { method: 'POST', body: formData, signal: controller.signal });
      if (!response.ok) {
        const text = await response.text();
        throw new Error(`Сервер ответил ${response.status}: ${text.slice(0, 160)}`);
      }
      const recognition = await response.json();
      setResult(recognition);
      await StorageService.saveRecognition({ ...recognition, imageUri: image, timestamp: new Date().toISOString() });
    } catch (error) {
      const message = error.name === 'AbortError' ? 'Сервер не ответил за 60 секунд.' : error.message || 'Не удалось распознать изображение';
      Alert.alert('Ошибка', `${message}\n\nЗапрос добавлен в очередь для повторной попытки.`);
      try {
        await enqueue();
      } catch (queueError) {
        console.error('Error adding to queue:', queueError);
      }
    } finally {
      clearTimeout(timeoutId);
      setLoading(false);
    }
  };

  const place = result && result.recognized ? result.object : null;
  const inRoute = place && routeIds.includes(place.id);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {!isConnected && <Notice tone="warn" icon="wifi-off">Нет сети — фото попадут в очередь и распознаются позже.</Notice>}
      <Text style={type.small}>Сфотографируйте достопримечательность — узнаем место и расскажем о нём.</Text>

      <Card style={styles.imageCard}>
        {image ? (
          <Image source={{ uri: image }} style={styles.image} accessibilityLabel="Выбранная фотография" />
        ) : (
          <View style={styles.placeholder}>
            <View style={styles.placeholderIcon}><Icon name="image-search-outline" size={34} color={colors.amur} /></View>
            <Text style={type.h3}>Фото пока не выбрано</Text>
            <Text style={[type.small, styles.center]}>Лучше всего работают снимки фасада целиком при дневном свете.</Text>
          </View>
        )}
      </Card>

      <View style={styles.row}>
        <Button title="Камера" icon="camera-outline" onPress={takePhoto} style={styles.flex} />
        <Button title="Галерея" icon="image-multiple-outline" variant="ghost" onPress={pickImage} style={styles.flex} />
      </View>
      {image ? (
        <Button
          title={loading ? 'Сопоставляем…' : 'Распознать место'}
          icon="magnify-scan"
          variant="gold"
          onPress={recognizeImage}
          loading={loading}
        />
      ) : null}
      {loading ? (
        <View style={styles.loadingRow}>
          <ActivityIndicator color={colors.amur} />
          <Text style={type.small}>Сравниваем фото с коллекцией мест края…</Text>
        </View>
      ) : null}

      {result && place ? (
        <Card style={styles.resultCard}>
          <Chip icon="check-circle-outline" label="Место распознано" tone="ok" />
          <Text style={type.title}>{place.name}</Text>
          <View style={styles.confidenceTrack}><View style={[styles.confidenceFill, { width: `${Math.round(result.confidence * 100)}%` }]} /></View>
          <Text style={type.small}>Уверенность {(result.confidence * 100).toFixed(1)}%</Text>
          <Text style={type.body}>{place.short_description || place.description}</Text>
          <View style={styles.chips}>
            <Chip icon="map-marker-outline" label={place.municipality} />
            {place.best_months_label ? <Chip icon="calendar-month-outline" label={place.best_months_label} /> : null}
            {place.visit_label ? <Chip icon="clock-outline" label={place.visit_label} tone="gold" /> : null}
          </View>
          <Button title="Подробнее о месте" icon="book-open-page-variant-outline" onPress={() => navigation.navigate('PlaceDetail', { id: place.id, name: place.name })} />
          <View style={styles.row}>
            <Button compact title={inRoute ? 'В маршруте' : 'В маршрут'} icon={inRoute ? 'check' : 'map-marker-plus-outline'} variant="ghost" onPress={() => toggleRoute(place.id)} style={styles.flex} />
            <Button compact title="Спросить гида" icon="robot-happy-outline" variant="gold" onPress={() => navigation.navigate('Guide', { objectId: place.id })} style={styles.flex} />
          </View>
        </Card>
      ) : null}

      {result && !place ? (
        <Card style={styles.resultCard}>
          <Notice tone="warn">Не удалось узнать место уверенно. Попробуйте другой ракурс или больше света.</Notice>
          {result.top_matches && result.top_matches.length ? (
            <>
              <Text style={type.label}>Возможно, это:</Text>
              <View style={styles.chips}>
                {result.top_matches.slice(0, 3).map(match => (
                  <Chip key={match.object_id} tone="white" label={match.name} onPress={() => navigation.navigate('PlaceDetail', { id: match.object_id, name: match.name })} />
                ))}
              </View>
            </>
          ) : null}
        </Card>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  content: { padding: spacing.lg, gap: spacing.md, paddingBottom: spacing.xxl },
  imageCard: { aspectRatio: 4 / 3, width: '100%', maxHeight: 360 },
  image: { width: '100%', height: '100%', resizeMode: 'cover' },
  placeholder: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: spacing.xl, gap: spacing.sm, backgroundColor: colors.sky },
  placeholderIcon: { width: 64, height: 64, borderRadius: 32, backgroundColor: colors.white, alignItems: 'center', justifyContent: 'center' },
  center: { textAlign: 'center' },
  row: { flexDirection: 'row', gap: spacing.sm },
  flex: { flex: 1 },
  loadingRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, justifyContent: 'center' },
  resultCard: { padding: spacing.lg, gap: spacing.sm },
  confidenceTrack: { height: 8, borderRadius: radius.pill, backgroundColor: colors.sky, overflow: 'hidden' },
  confidenceFill: { height: '100%', backgroundColor: colors.ok },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
});
