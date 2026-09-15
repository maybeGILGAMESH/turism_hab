import React, { useCallback, useEffect, useRef, useState } from 'react';
import { FlatList, KeyboardAvoidingView, Linking, Platform, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Chip, Icon, IconButton } from '../components/ui';
import { useAppState } from '../context/AppState';
import { Api } from '../services/api';
import { StorageService } from '../services/StorageService';
import { colors, radius, spacing, touch, type } from '../theme';

const DEFAULT_SUGGESTIONS = [
  'Что посмотреть в Хабаровске за один день?',
  'Когда цветут лотосы у Галкино?',
  'Что взять с собой на петроглифы Сикачи-Аляна?',
];
const MAX_LENGTH = 1000;

function Bubble({ turn }) {
  if (turn.role === 'user') {
    return <View style={[styles.bubble, styles.userBubble]}><Text style={styles.userText}>{turn.content}</Text></View>;
  }
  const meta = turn.meta || {};
  return (
    <View style={[styles.bubble, styles.botBubble, meta.error && styles.errorBubble]}>
      <Text style={type.body}>{turn.content}</Text>
      {(meta.warnings || []).map(warning => <Text key={warning} style={styles.warning}>{warning}</Text>)}
      <Text style={styles.footer}>
        {meta.mode === 'local_llm' ? 'Локальная модель' : 'Ответ из базы знаний'}
        {meta.grounded === false ? ' · нет подтверждения в базе' : ''}
      </Text>
      {(meta.sources || []).map(source => (
        <Pressable key={source.url} onPress={() => Linking.openURL(source.url)} accessibilityRole="link" style={styles.sourceLink}>
          <Icon name="open-in-new" size={14} color={colors.amur600} />
          <Text style={styles.sourceText} numberOfLines={2}>{source.title}</Text>
        </Pressable>
      ))}
    </View>
  );
}

export default function GuideScreen({ route, navigation }) {
  const { apiUrl, objectsById, routeIds, travelMode } = useAppState();
  const insets = useSafeAreaInsets();
  const [turns, setTurns] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [contextId, setContextId] = useState(route.params?.objectId || null);
  const [status, setStatus] = useState(null);
  const listRef = useRef(null);
  const initialQuestion = useRef(route.params?.question || null);
  const loaded = useRef(false);

  useEffect(() => {
    StorageService.getGuideHistory().then(history => {
      setTurns(history);
      loaded.current = true;
    });
    Api.assistantStatus(apiUrl).then(setStatus).catch(() => setStatus({ llm_available: false, offline: true }));
  }, [apiUrl]);

  useEffect(() => {
    setContextId(route.params?.objectId || null);
  }, [route.params?.objectId]);

  useEffect(() => {
    navigation.setOptions({
      headerRight: () => (
        <IconButton icon="delete-sweep-outline" label="Очистить диалог" color={colors.white} onPress={() => { setTurns([]); StorageService.clearGuideHistory(); }} style={{ marginRight: 4 }} />
      ),
    });
  }, [navigation]);

  const send = useCallback(async text => {
    const message = String(text || '').trim().slice(0, MAX_LENGTH);
    if (!message || sending) return;
    const history = turns.slice(-8).map(turn => ({ role: turn.role, content: turn.content.slice(0, 2000) }));
    const withQuestion = [...turns, { id: `${Date.now()}-u`, role: 'user', content: message }];
    setTurns(withQuestion);
    setInput('');
    setSending(true);
    let answerTurn;
    try {
      const data = await Api.chat(apiUrl, {
        message,
        object_id: contextId,
        route_object_ids: routeIds,
        travel_mode: travelMode,
        history,
      });
      answerTurn = {
        id: `${Date.now()}-a`,
        role: 'assistant',
        content: data.answer,
        meta: { mode: data.mode, grounded: data.grounded, sources: data.sources, warnings: data.warnings, suggested: data.suggested_questions },
      };
    } catch (error) {
      answerTurn = { id: `${Date.now()}-e`, role: 'assistant', content: error.message, meta: { error: true, grounded: false } };
    }
    const next = [...withQuestion, answerTurn];
    setTurns(next);
    StorageService.saveGuideHistory(next);
    setSending(false);
  }, [apiUrl, contextId, routeIds, travelMode, turns, sending]);

  useEffect(() => {
    if (initialQuestion.current && loaded.current !== null) {
      const question = initialQuestion.current;
      initialQuestion.current = null;
      setTimeout(() => send(question), 300);
    }
  }, [send]);

  const last = turns[turns.length - 1];
  const suggestions = sending ? [] : (last && last.meta && last.meta.suggested) || (turns.length ? [] : DEFAULT_SUGGESTIONS);
  const contextName = contextId ? objectsById.get(contextId)?.name : null;

  return (
    <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined} keyboardVerticalOffset={Platform.OS === 'ios' ? 64 : 0}>
      <View style={styles.statusRow}>
        <View style={[styles.statusDot, { backgroundColor: status?.llm_available ? colors.ok : colors.warn }]} />
        <Text style={type.small} numberOfLines={1}>
          {status == null ? 'Проверяем гида…' : status.offline ? 'Сервер недоступен' : status.llm_available ? 'Локальная модель · без облака' : 'Резервный режим: ответы из базы знаний'}
        </Text>
      </View>
      <FlatList
        ref={listRef}
        data={turns}
        keyExtractor={item => item.id}
        contentContainerStyle={styles.list}
        onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: true })}
        ListHeaderComponent={
          <View style={[styles.bubble, styles.botBubble]}>
            <Text style={type.body}>Здравствуйте! Я локальный гид по Хабаровскому краю: расскажу об истории мест, сезоне, экипировке и времени поездки — только по проверенной базе знаний.</Text>
          </View>
        }
        renderItem={({ item }) => <Bubble turn={item} />}
        ListFooterComponent={
          <View style={styles.footerArea}>
            {sending ? <Text style={type.small}>Гид печатает…</Text> : null}
            <View style={styles.suggestions}>
              {suggestions.map(question => <Chip key={question} tone="white" label={question} onPress={() => send(question)} />)}
            </View>
          </View>
        }
      />
      <View style={[styles.composer, { paddingBottom: spacing.sm + insets.bottom }]}>
        {contextName ? (
          <View style={styles.context}>
            <Icon name="map-marker-outline" size={16} color={colors.goldInk} />
            <Text style={styles.contextText} numberOfLines={1}>О месте: {contextName}</Text>
            <IconButton icon="close" label="Убрать контекст места" color={colors.goldInk} onPress={() => setContextId(null)} style={styles.contextClose} />
          </View>
        ) : routeIds.length ? (
          <View style={styles.context}><Icon name="map-marker-path" size={16} color={colors.goldInk} /><Text style={styles.contextText}>Учитываю маршрут: {routeIds.length} мест</Text></View>
        ) : null}
        <View style={styles.inputRow}>
          <TextInput
            value={input}
            onChangeText={setInput}
            placeholder="История, сезон, что взять, сколько ехать…"
            placeholderTextColor={colors.muted}
            style={styles.input}
            multiline
            maxLength={MAX_LENGTH}
            accessibilityLabel="Вопрос гиду"
          />
          <Pressable
            onPress={() => send(input)}
            disabled={!input.trim() || sending}
            accessibilityRole="button"
            accessibilityLabel="Отправить вопрос"
            style={[styles.send, (!input.trim() || sending) && styles.sendDisabled]}
          >
            <Icon name="send" size={22} color={colors.white} />
          </Pressable>
        </View>
        <Text style={styles.counter}>{input.length} / {MAX_LENGTH}</Text>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  statusRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, paddingHorizontal: spacing.lg, paddingVertical: spacing.sm, backgroundColor: colors.white, borderBottomWidth: 1, borderBottomColor: colors.line },
  statusDot: { width: 9, height: 9, borderRadius: 5 },
  list: { padding: spacing.lg, gap: spacing.sm },
  bubble: { maxWidth: '88%', borderRadius: radius.lg, padding: spacing.md, marginBottom: spacing.sm, gap: 4 },
  userBubble: { alignSelf: 'flex-end', backgroundColor: colors.amur, borderBottomRightRadius: 4 },
  userText: { color: colors.white, fontSize: 15, lineHeight: 22 },
  botBubble: { alignSelf: 'flex-start', backgroundColor: colors.white, borderWidth: 1, borderColor: colors.line, borderBottomLeftRadius: 4 },
  errorBubble: { backgroundColor: colors.badSoft, borderColor: '#F0C9C4' },
  warning: { fontSize: 12, lineHeight: 17, color: colors.goldInk },
  footer: { fontSize: 12, color: colors.muted, marginTop: 2 },
  sourceLink: { flexDirection: 'row', alignItems: 'center', gap: 4, minHeight: 32 },
  sourceText: { fontSize: 13, color: colors.amur600, flexShrink: 1, textDecorationLine: 'underline' },
  footerArea: { gap: spacing.sm },
  suggestions: { gap: 6 },
  composer: { borderTopWidth: 1, borderTopColor: colors.line, backgroundColor: colors.white, paddingHorizontal: spacing.md, paddingTop: spacing.sm, gap: 6 },
  context: { flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: colors.goldSoft, borderRadius: radius.pill, paddingLeft: spacing.md, minHeight: 36, alignSelf: 'flex-start', maxWidth: '100%' },
  contextText: { color: colors.goldInk, fontSize: 13, flexShrink: 1, paddingRight: spacing.sm },
  contextClose: { width: 36, height: 36 },
  inputRow: { flexDirection: 'row', alignItems: 'flex-end', gap: spacing.sm },
  input: { flex: 1, minHeight: touch, maxHeight: 120, borderWidth: 1, borderColor: colors.line, borderRadius: radius.md, paddingHorizontal: spacing.md, paddingVertical: 10, fontSize: 16, color: colors.ink, backgroundColor: colors.bg },
  send: { width: 48, height: 48, borderRadius: 24, backgroundColor: colors.amur, alignItems: 'center', justifyContent: 'center' },
  sendDisabled: { opacity: 0.45 },
  counter: { fontSize: 11, color: colors.muted, textAlign: 'right' },
});
