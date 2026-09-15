import React, { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Image, Linking, ScrollView, StyleSheet, Text, View, useWindowDimensions } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Button, Card, Chip, Icon, Notice, Segmented } from '../components/ui';
import { useAppState } from '../context/AppState';
import { Api, imageUrl } from '../services/api';
import { CATEGORY_LABELS, colors, spacing, type } from '../theme';

function Section({ icon, title, children }) {
  return (
    <View style={styles.section}>
      <View style={styles.sectionHead}><Icon name={icon} size={20} color={colors.amur} /><Text style={type.h3}>{title}</Text></View>
      {children}
    </View>
  );
}

function Bullets({ items }) {
  if (!items || !items.length) return <Text style={type.small}>Нет данных.</Text>;
  return items.map((item, index) => (
    <View key={index} style={styles.bullet}>
      <View style={styles.dot} />
      <Text style={[type.body, styles.flex]}>{item}</Text>
    </View>
  ));
}

export default function PlaceDetailScreen({ route, navigation }) {
  const { id } = route.params || {};
  const { apiUrl, routeIds, toggleRoute } = useAppState();
  const insets = useSafeAreaInsets();
  const { width } = useWindowDimensions();
  const [place, setPlace] = useState(null);
  const [error, setError] = useState('');
  const [season, setSeason] = useState('summer');

  const load = useCallback(async () => {
    setError('');
    try {
      const data = await Api.object(apiUrl, id);
      setPlace(data);
      navigation.setOptions({ title: data.name });
    } catch (reason) {
      setError(reason.message);
    }
  }, [apiUrl, id, navigation]);

  useEffect(() => { load(); }, [load]);

  if (error) {
    return <View style={styles.center}><Notice tone="bad">{error}</Notice><Button compact title="Повторить" icon="refresh" onPress={load} /></View>;
  }
  if (!place) {
    return <View style={styles.center}><ActivityIndicator color={colors.amur} /></View>;
  }

  const inRoute = routeIds.includes(place.id);
  const photos = (place.example_images || []).map(path => imageUrl(apiUrl, path));
  const photoWidth = Math.min(width, 720);

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={{ paddingBottom: 96 + insets.bottom }}>
        {photos.length ? (
          <ScrollView horizontal pagingEnabled showsHorizontalScrollIndicator={false} style={styles.gallery}>
            {photos.map(uri => <Image key={uri} source={{ uri }} style={[styles.photo, { width: photoWidth }]} accessibilityLabel={place.name} />)}
          </ScrollView>
        ) : null}
        <View style={styles.content}>
          <Text style={type.title}>{place.name}</Text>
          <View style={styles.meta}><Icon name="map-marker-outline" size={16} color={colors.muted} /><Text style={[type.small, styles.flex]}>{place.municipality}{place.address ? ` · ${place.address}` : ''}</Text></View>
          <View style={styles.chips}>
            <Chip label={CATEGORY_LABELS[place.category] || place.category} />
            {place.best_months_label ? <Chip icon="calendar-month-outline" label={place.best_months_label} /> : null}
            {place.visit_label ? <Chip icon="clock-outline" label={place.visit_label} /> : null}
            {place.difficulty_label ? <Chip icon="speedometer" label={place.difficulty_label} tone="gold" /> : null}
            {place.accessibility_label ? <Chip icon="wheelchair-accessibility" label={place.accessibility_label} /> : null}
          </View>
          <Text style={[type.body, styles.lead]}>{place.short_description || place.description}</Text>

          {place.content_available ? (
            <>
              <Text style={type.body}>{place.full_description}</Text>
              <Section icon="book-open-variant" title="История"><Text style={type.body}>{place.history}</Text></Section>
              <Section icon="star-outline" title="Интересные особенности"><Bullets items={place.highlights} /></Section>
              <Section icon="calendar-month-outline" title="Когда ехать">
                <Text style={type.body}><Text style={styles.bold}>{place.best_months_label}. </Text>{place.seasonal_notes}</Text>
              </Section>
              <Section icon="map-marker-path" title="Как добраться">
                <Text style={type.body}>{place.transport}</Text>
                <Text style={type.small}>{place.trip_profile_label} · осмотр {place.visit_label}</Text>
              </Section>
              <Section icon="human-male-child" title="Семьям с детьми"><Text style={type.body}>{place.family_tips}</Text></Section>
              <Section icon="wheelchair-accessibility" title="Маломобильным посетителям"><Text style={type.body}>{place.reduced_mobility_tips}</Text></Section>
              <Section icon="bag-personal-outline" title="Что взять с собой">
                <Segmented
                  value={season}
                  onChange={setSeason}
                  options={[{ value: 'summer', label: 'Лето' }, { value: 'winter', label: 'Зима' }, { value: 'offseason', label: 'Межсезонье' }]}
                />
                <View style={styles.gap}><Bullets items={place.packing[season]} /></View>
              </Section>
              <Section icon="shield-alert-outline" title="Безопасность"><Bullets items={place.safety} /></Section>
              <Section icon="hand-heart-outline" title="Этикет"><Bullets items={place.etiquette} /></Section>
              <Section icon="lightbulb-on-outline" title="Практические советы"><Bullets items={place.practical_tips} /></Section>
              <Section icon="link-variant" title="Источники">
                {place.sources.map(source => (
                  <Button key={source.url} compact variant="ghost" icon="open-in-new" title={source.title} onPress={() => Linking.openURL(source.url)} style={styles.sourceButton} />
                ))}
                <Text style={type.small}>
                  Проверено: {place.verified_at}
                  {place.review_status === 'needs_editor_review' ? ' · часть сведений ожидает редакторской проверки' : ''}. Цены и расписания уточняйте в официальных источниках.
                </Text>
              </Section>
            </>
          ) : (
            <Card style={styles.cardPad}><Text style={type.small}>Расширенная карточка для этого места ещё не подготовлена.</Text></Card>
          )}
        </View>
      </ScrollView>
      <View style={[styles.actionBar, { paddingBottom: spacing.sm + insets.bottom }]}>
        <Button compact variant="ghost" title={inRoute ? 'В маршруте' : 'В маршрут'} icon={inRoute ? 'check' : 'map-marker-plus-outline'} onPress={() => toggleRoute(place.id)} style={styles.flex} />
        <Button compact variant="gold" title="Спросить гида" icon="robot-happy-outline" onPress={() => navigation.navigate('Guide', { objectId: place.id })} style={styles.flex} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: spacing.lg, gap: spacing.md, backgroundColor: colors.bg },
  gallery: { backgroundColor: colors.sky },
  photo: { aspectRatio: 16 / 10, maxHeight: 380 },
  content: { padding: spacing.lg, gap: spacing.sm },
  meta: { flexDirection: 'row', alignItems: 'flex-start', gap: 4 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  lead: { fontSize: 17, lineHeight: 25, marginTop: spacing.xs },
  section: { borderTopWidth: 1, borderTopColor: colors.line, paddingTop: spacing.md, marginTop: spacing.sm, gap: 6 },
  sectionHead: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  bullet: { flexDirection: 'row', gap: spacing.sm, alignItems: 'flex-start' },
  dot: { width: 6, height: 6, borderRadius: 3, backgroundColor: colors.gold, marginTop: 8 },
  flex: { flex: 1 },
  bold: { fontWeight: '700' },
  gap: { marginTop: spacing.sm, gap: 6 },
  sourceButton: { justifyContent: 'flex-start' },
  cardPad: { padding: spacing.lg },
  actionBar: { position: 'absolute', left: 0, right: 0, bottom: 0, flexDirection: 'row', gap: spacing.sm, padding: spacing.sm, paddingHorizontal: spacing.lg, backgroundColor: colors.white, borderTopWidth: 1, borderTopColor: colors.line },
});
