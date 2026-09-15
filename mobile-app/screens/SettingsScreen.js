import React, { useEffect, useState } from 'react';
import { Alert, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { Button, Card, SectionTitle } from '../components/ui';
import { API_PORT, APP_VERSION, STREAMLIT_PORT } from '../config';
import { StorageService } from '../services/StorageService';
import { colors, radius, spacing, type } from '../theme';

export default function SettingsScreen({ apiUrl, onSettingsChange }) {
  const [serverUrl, setServerUrl] = useState(apiUrl || `http://localhost:${API_PORT}`);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    StorageService.getSettings().then(settings => setServerUrl(settings.serverUrl || apiUrl));
  }, [apiUrl]);

  const saveConfirmed = async value => {
    await StorageService.saveSettings({ serverUrl: value });
    setSaved(true);
    if (onSettingsChange) onSettingsChange(value);
    setTimeout(() => setSaved(false), 2000);
  };

  const saveSettings = async () => {
    const value = serverUrl.trim().replace(/\/+$/, '');
    if (!/^https?:\/\/.+/.test(value)) {
      Alert.alert('Неверный адрес', 'Используйте формат http://ip-адрес:порт');
      return;
    }
    let url;
    try {
      url = new URL(value);
    } catch (error) {
      Alert.alert('Неверный адрес', 'Используйте формат http://ip-адрес:порт');
      return;
    }
    if (url.port === String(STREAMLIT_PORT) || url.port === '8501') {
      const corrected = `${url.protocol}//${url.hostname}:${API_PORT}`;
      Alert.alert('Порт Streamlit', `Порт ${url.port} — это веб-панель. Мобильному приложению нужен API на порту ${API_PORT}.`, [
        { text: 'Отмена', style: 'cancel' },
        { text: `Исправить на ${API_PORT}`, onPress: () => { setServerUrl(corrected); saveConfirmed(corrected); } },
      ]);
      return;
    }
    if (url.port && url.port !== String(API_PORT)) {
      Alert.alert('Проверьте порт', `API версии 3.0 работает на порту ${API_PORT}. Порт 8000 — у стабильной версии 2.0.`, [
        { text: 'Отмена', style: 'cancel' },
        { text: 'Сохранить всё равно', onPress: () => saveConfirmed(value) },
      ]);
      return;
    }
    await saveConfirmed(value);
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Card style={styles.card}>
        <SectionTitle icon="server-network">Подключение к серверу</SectionTitle>
        <Text style={type.label}>Адрес API</Text>
        <TextInput
          style={styles.input}
          value={serverUrl}
          onChangeText={setServerUrl}
          placeholder={`http://192.168.1.100:${API_PORT}`}
          placeholderTextColor={colors.muted}
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="url"
          accessibilityLabel="Адрес API"
        />
        <Text style={type.small}>Эмулятор Android — http://10.0.2.2:{API_PORT}, браузер — http://localhost:{API_PORT}, телефон — IP компьютера в локальной сети.</Text>
        <Button title={saved ? 'Сохранено' : 'Сохранить'} icon={saved ? 'check' : 'content-save-outline'} variant={saved ? 'success' : 'primary'} onPress={saveSettings} />
      </Card>

      <Card style={styles.card}>
        <SectionTitle icon="information-outline">О приложении</SectionTitle>
        <Text style={type.body}>Потребительский гид по достопримечательностям Хабаровского края.</Text>
        <Text style={type.small}>Версия {APP_VERSION}. Карточки мест содержат источники и дату проверки; ИИ-гид работает на локальной модели без облачных сервисов, а история диалога хранится только на устройстве.</Text>
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  content: { padding: spacing.lg, gap: spacing.md },
  card: { padding: spacing.lg, gap: spacing.sm },
  input: { minHeight: 48, borderWidth: 1, borderColor: colors.line, borderRadius: radius.md, paddingHorizontal: spacing.md, fontSize: 16, color: colors.ink, backgroundColor: colors.white },
});
