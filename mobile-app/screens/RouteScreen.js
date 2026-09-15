import React, { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Button, Card, Chip, EmptyState, Icon, IconButton, Notice, Segmented } from '../components/ui';
import { useAppState } from '../context/AppState';
import { Api } from '../services/api';
import { colors, formatMinutes, formatRange, radius, spacing, type } from '../theme';

const TIME_OPTIONS = [
  { value: null, label: 'Без ограничения' },
  { value: 120, label: '2 часа' },
  { value: 240, label: '4 часа' },
  { value: 480, label: 'Весь день' },
];
const CITY_CENTER = { latitude: 48.48, longitude: 135.071 };

export default function RouteScreen({ navigation }) {
  const { apiUrl, objectsById, routeIds, toggleRoute, replaceRoute, clearRoute, travelMode, setTravelMode } = useAppState();
  const [available, setAvailable] = useState(null);
  const [auto, setAuto] = useState(false);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const calculate = useCallback(async () => {
    if (!routeIds.length && !auto) {
      setResult(null);
      return;
    }
    setLoading(true);
    setError('');
    const body = { travel_mode: travelMode };
    if (available) body.available_minutes = available;
    if (routeIds.length) body.object_ids = routeIds;
    else Object.assign(body, CITY_CENTER, { limit: 6 });
    try {
      setResult(await Api.planRoute(apiUrl, body));
    } catch (reason) {
      setError(reason.message);
    } finally {
      setLoading(false);
    }
  }, [apiUrl, routeIds, travelMode, available, auto]);

  useEffect(() => { calculate(); }, [calculate]);

  const summary = result && result.summary;
  const remote = summary && summary.has_remote_objects;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Segmented
        value={travelMode}
        onChange={setTravelMode}
        options={[{ value: 'walk', label: 'Пешком', icon: 'walk' }, { value: 'car', label: 'Автомобиль', icon: 'car-outline' }]}
      />
      <View>
        <Text style={type.label}>Сколько у вас времени</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipRow}>
          {TIME_OPTIONS.map(option => (
            <Chip key={option.label} tone="white" label={option.label} selected={available === option.value} onPress={() => setAvailable(option.value)} />
          ))}
        </ScrollView>
      </View>

      <Card style={styles.pad}>
        <View style={styles.rowBetween}>
          <Text style={type.h2}>Места маршрута</Text>
          {routeIds.length ? <Button compact variant="danger" title="Очистить" icon="delete-outline" onPress={() => { clearRoute(); setAuto(false); }} /> : null}
        </View>
        {routeIds.length ? routeIds.map(id => (
          <View key={id} style={styles.stopRow}>
            <Icon name="map-marker-outline" size={18} color={colors.amur} />
            <Text style={[type.body, styles.flex]} numberOfLines={2}>{objectsById.get(id)?.name || `Место #${id}`}</Text>
            <IconButton icon="close" label="Убрать из маршрута" onPress={() => toggleRoute(id)} color={colors.muted} />
          </View>
        )) : (
          <EmptyState icon="map-marker-path" title="Маршрут пуст" text="Добавьте места в каталоге или подберите прогулку по историческому центру Хабаровска.">
            <View style={styles.row}>
              <Button compact title="Подобрать прогулку" icon="auto-fix" onPress={() => setAuto(true)} />
              <Button compact variant="ghost" title="Каталог" icon="map-search-outline" onPress={() => navigation.navigate('Main', { screen: 'Explore' })} />
            </View>
          </EmptyState>
        )}
      </Card>

      {loading ? <View style={styles.loading}><ActivityIndicator color={colors.amur} /><Text style={type.small}>Считаем время…</Text></View> : null}
      {error ? <Notice tone="bad">{error}</Notice> : null}

      {result && result.route.length ? (
        <>
          <View style={styles.stats}>
            <View style={styles.stat}><Text style={type.label}>В пути</Text><Text style={styles.statValue}>{remote ? formatRange(summary.travel_minutes_range) : formatMinutes(summary.travel_minutes)}</Text><Text style={type.small}>≈ {summary.estimated_road_km} км</Text></View>
            <View style={styles.stat}><Text style={type.label}>На осмотр</Text><Text style={styles.statValue}>{formatMinutes(summary.visit_minutes)}</Text><Text style={type.small}>{formatRange(summary.visit_minutes_range)}</Text></View>
          </View>
          <View style={[styles.stat, styles.statTotal]}>
            <Text style={[type.label, styles.white]}>Итого</Text>
            <Text style={[styles.statValue, styles.white]}>{remote ? formatRange(summary.total_minutes_range) : formatMinutes(summary.total_minutes)}</Text>
            <Text style={[type.small, styles.white]}>
              {summary.available_minutes ? (summary.fits_available_time ? 'Укладывается в ваше время' : 'Не укладывается в ваше время') : 'Ориентировочная оценка'}
            </Text>
          </View>
          {result.warnings.map(warning => <Notice key={warning}>{warning}</Notice>)}

          <View>
            {result.route.map((item, index) => {
              const leg = item.leg;
              const travel = leg ? (leg.is_range ? formatRange(leg.travel_minutes_range) : formatMinutes(leg.travel_minutes)) : '';
              return (
                <View key={item.id} style={styles.timelineItem}>
                  <View style={styles.rail}>
                    <View style={styles.num}><Text style={styles.numText}>{item.order}</Text></View>
                    {index < result.route.length - 1 ? <View style={styles.line} /> : null}
                  </View>
                  <View style={styles.flex}>
                    <View style={styles.leg}>
                      <Icon name={leg ? (leg.mode === 'walk' ? 'walk' : 'car-outline') : 'flag-outline'} size={16} color={colors.muted} />
                      <Text style={type.small}>{leg ? `${leg.estimated_road_km} км · ~${travel}` : 'Старт маршрута'}</Text>
                    </View>
                    <Card onPress={() => navigation.navigate('PlaceDetail', { id: item.id, name: item.name })} style={styles.stopCard} accessibilityLabel={`${item.name}, открыть карточку`}>
                      <Text style={type.h3}>{item.name}</Text>
                      <Text style={type.small}>Осмотр ~{formatMinutes(item.visit_minutes.planned)} · через {formatMinutes(item.arrival_after_minutes)} от старта</Text>
                    </Card>
                  </View>
                </View>
              );
            })}
          </View>
          <Text style={type.small}>{result.estimation.description}</Text>
          {!routeIds.length ? <Button variant="ghost" title="Сохранить эти места в маршрут" icon="content-save-outline" onPress={() => { replaceRoute(result.route.map(item => item.id)); setAuto(false); }} /> : null}
          <Button
            variant="gold"
            title="Спросить гида о маршруте"
            icon="robot-happy-outline"
            onPress={() => {
              if (!routeIds.length) replaceRoute(result.route.map(item => item.id));
              navigation.navigate('Guide', { question: 'Сколько времени займёт мой маршрут и что взять с собой?' });
            }}
          />
        </>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  content: { padding: spacing.lg, gap: spacing.md, paddingBottom: spacing.xxl },
  chipRow: { gap: 6, paddingTop: 6 },
  pad: { padding: spacing.lg, gap: spacing.xs },
  rowBetween: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: spacing.sm },
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm, justifyContent: 'center', marginTop: spacing.sm },
  stopRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, borderBottomWidth: 1, borderBottomColor: colors.line, paddingLeft: spacing.xs },
  flex: { flex: 1 },
  loading: { flexDirection: 'row', gap: spacing.sm, alignItems: 'center', justifyContent: 'center' },
  stats: { flexDirection: 'row', gap: spacing.sm },
  stat: { flex: 1, backgroundColor: colors.sky, borderRadius: radius.md, padding: spacing.md, gap: 2 },
  statTotal: { backgroundColor: colors.amur },
  statValue: { fontSize: 20, fontWeight: '700', color: colors.amurDark },
  white: { color: colors.white },
  timelineItem: { flexDirection: 'row', gap: spacing.md },
  rail: { alignItems: 'center', width: 32 },
  num: { width: 32, height: 32, borderRadius: 16, backgroundColor: colors.amur, alignItems: 'center', justifyContent: 'center' },
  numText: { color: colors.white, fontWeight: '700' },
  line: { flex: 1, width: 2, backgroundColor: colors.sky2, marginVertical: 4 },
  leg: { flexDirection: 'row', alignItems: 'center', gap: 4, minHeight: 32 },
  stopCard: { padding: spacing.md, marginBottom: spacing.md, gap: 2 },
});
