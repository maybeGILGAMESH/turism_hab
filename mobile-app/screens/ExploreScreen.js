import React, { useMemo, useState } from 'react';
import { ActivityIndicator, FlatList, Image, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { Button, Card, Chip, EmptyState, Icon, Notice } from '../components/ui';
import { useAppState } from '../context/AppState';
import { imageUrl } from '../services/api';
import { CATEGORY_LABELS, colors, radius, spacing, type } from '../theme';

const FORMATS = [
  { value: '', label: 'Все' },
  { value: 'urban', label: 'Город' },
  { value: 'regional', label: 'На день' },
  { value: 'remote', label: 'Экспедиции' },
];
const SEASONS = [
  { value: '', label: 'Любой сезон' },
  { value: 'summer', label: 'Лето' },
  { value: 'winter', label: 'Зима' },
  { value: 'autumn', label: 'Осень' },
  { value: 'spring', label: 'Весна' },
];

function PlaceCard({ item, apiUrl, inRoute, onOpen, onToggleRoute, onAsk }) {
  const photo = imageUrl(apiUrl, item.example_images && item.example_images[0]);
  return (
    <Card onPress={onOpen} style={styles.card} accessibilityLabel={`${item.name}, открыть карточку`}>
      <View style={styles.media}>
        {photo ? <Image source={{ uri: photo }} style={styles.image} /> : <View style={styles.imagePlaceholder}><Icon name="image-filter-hdr" size={36} color={colors.amur} /></View>}
        <View style={styles.badge}><Text style={styles.badgeText}>{CATEGORY_LABELS[item.category] || item.category}</Text></View>
        {item.trip_profile === 'remote' ? <View style={[styles.badge, styles.badgeRight]}><Text style={[styles.badgeText, { color: colors.goldInk }]}>Экспедиция</Text></View> : null}
      </View>
      <View style={styles.body}>
        <View style={styles.meta}><Icon name="map-marker-outline" size={15} color={colors.muted} /><Text style={type.small} numberOfLines={1}>{item.municipality}</Text></View>
        <Text style={type.h3}>{item.name}</Text>
        <Text style={type.small} numberOfLines={3}>{item.short_description || item.description}</Text>
        <View style={styles.chips}>
          {item.best_months_label ? <Chip icon="calendar-month-outline" label={item.best_months_label} /> : null}
          {item.visit_label ? <Chip icon="clock-outline" label={item.visit_label} /> : null}
          {item.difficulty_label ? <Chip icon="speedometer" label={item.difficulty_label} tone="gold" /> : null}
        </View>
        <View style={styles.actions}>
          <Button compact variant="ghost" title={inRoute ? 'В маршруте' : 'В маршрут'} icon={inRoute ? 'check' : 'map-marker-plus-outline'} onPress={onToggleRoute} style={styles.flex} />
          <Button compact variant="ghost" title="Гид" icon="robot-happy-outline" onPress={onAsk} accessibilityLabel={`Спросить гида о месте ${item.name}`} />
        </View>
      </View>
    </Card>
  );
}

export default function ExploreScreen({ navigation }) {
  const { apiUrl, objects, loadingObjects, objectsError, reloadObjects, routeIds, toggleRoute } = useAppState();
  const [query, setQuery] = useState('');
  const [format, setFormat] = useState('');
  const [season, setSeason] = useState('');

  const filtered = useMemo(() => objects.filter(item =>
    `${item.name} ${item.municipality}`.toLowerCase().includes(query.trim().toLowerCase())
    && (!format || item.trip_profile === format)
    && (!season || (item.seasons || []).includes(season))), [objects, query, format, season]);

  if (loadingObjects && !objects.length) {
    return <View style={styles.center}><ActivityIndicator color={colors.amur} /><Text style={type.small}>Загружаем каталог…</Text></View>;
  }

  const header = (
    <View style={styles.header}>
      <View style={styles.search}>
        <Icon name="magnify" size={20} color={colors.muted} />
        <TextInput
          value={query}
          onChangeText={setQuery}
          placeholder="Название или район"
          placeholderTextColor={colors.muted}
          style={styles.searchInput}
          accessibilityLabel="Поиск мест"
          returnKeyType="search"
        />
      </View>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filterRow}>
        {FORMATS.map(option => <Chip key={option.value || 'all'} tone="white" label={option.label} selected={format === option.value} onPress={() => setFormat(option.value)} />)}
      </ScrollView>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filterRow}>
        {SEASONS.map(option => <Chip key={option.value || 'any'} tone="white" label={option.label} selected={season === option.value} onPress={() => setSeason(option.value)} />)}
      </ScrollView>
      {objectsError ? <Notice tone="bad">{objectsError}</Notice> : null}
      <Text style={type.label}>{filtered.length} из {objects.length} мест</Text>
    </View>
  );

  return (
    <View style={styles.container}>
      <FlatList
        data={filtered}
        keyExtractor={item => String(item.id)}
        ListHeaderComponent={header}
        contentContainerStyle={styles.list}
        refreshing={loadingObjects}
        onRefresh={reloadObjects}
        ListEmptyComponent={
          <EmptyState icon="map-search-outline" title={objectsError ? 'Каталог недоступен' : 'Ничего не найдено'} text={objectsError ? 'Проверьте адрес сервера в настройках.' : 'Измените поиск или фильтры.'}>
            {objectsError ? <Button compact title="Повторить" icon="refresh" onPress={reloadObjects} /> : null}
          </EmptyState>
        }
        renderItem={({ item }) => (
          <PlaceCard
            item={item}
            apiUrl={apiUrl}
            inRoute={routeIds.includes(item.id)}
            onOpen={() => navigation.navigate('PlaceDetail', { id: item.id, name: item.name })}
            onToggleRoute={() => toggleRoute(item.id)}
            onAsk={() => navigation.navigate('Guide', { objectId: item.id })}
          />
        )}
      />
      <View style={styles.routeBar}>
        <View style={styles.routeInfo}>
          <Icon name="map-marker-path" size={22} color={colors.white} />
          <Text style={styles.routeText} numberOfLines={1}>{routeIds.length ? `В маршруте: ${routeIds.length}` : 'Маршрут по центру Хабаровска'}</Text>
        </View>
        <Button compact variant="gold" title={routeIds.length ? 'Рассчитать' : 'Подобрать'} icon="clock-fast" onPress={() => navigation.navigate('Route')} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: spacing.sm, backgroundColor: colors.bg },
  list: { padding: spacing.lg, paddingBottom: 96, gap: spacing.md },
  header: { gap: spacing.sm, marginBottom: spacing.xs },
  search: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, backgroundColor: colors.white, borderWidth: 1, borderColor: colors.line, borderRadius: radius.md, paddingHorizontal: spacing.md, minHeight: 48 },
  searchInput: { flex: 1, fontSize: 16, color: colors.ink, paddingVertical: 10 },
  filterRow: { gap: 6, paddingRight: spacing.lg },
  card: { marginBottom: spacing.md },
  media: { aspectRatio: 16 / 9, backgroundColor: colors.sky },
  image: { width: '100%', height: '100%' },
  imagePlaceholder: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  badge: { position: 'absolute', top: 10, left: 10, backgroundColor: 'rgba(255,255,255,0.94)', borderRadius: radius.pill, paddingHorizontal: 10, paddingVertical: 4 },
  badgeRight: { left: undefined, right: 10, backgroundColor: colors.goldSoft },
  badgeText: { fontSize: 12, fontWeight: '700', color: colors.amurDark },
  body: { padding: spacing.md, gap: 6 },
  meta: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 2 },
  actions: { flexDirection: 'row', gap: spacing.sm, marginTop: spacing.xs },
  flex: { flex: 1 },
  routeBar: { position: 'absolute', left: spacing.md, right: spacing.md, bottom: spacing.md, backgroundColor: colors.amurDark, borderRadius: radius.lg, padding: spacing.sm, paddingLeft: spacing.md, flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  routeInfo: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  routeText: { color: colors.white, fontWeight: '700', flexShrink: 1 },
});
