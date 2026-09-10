import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  Alert,
  ScrollView,
} from 'react-native';
import { StorageService } from '../services/StorageService';

export default function SettingsScreen({ apiUrl, onSettingsChange }) {
  const [serverUrl, setServerUrl] = useState(apiUrl || 'http://192.168.0.102:8000');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const settings = await StorageService.getSettings();
      if (settings.serverUrl) {
        setServerUrl(settings.serverUrl);
      } else if (apiUrl) {
        setServerUrl(apiUrl);
      }
    } catch (error) {
      console.error('Error loading settings:', error);
    }
  };

  const saveSettings = async () => {
    try {
      // Валидация URL
      const urlPattern = /^https?:\/\/.+/;
      if (!urlPattern.test(serverUrl.trim())) {
        Alert.alert('Ошибка', 'Неверный формат URL. Используйте формат: http://ip-адрес:порт');
        return;
      }

      // Предупреждение о неправильном порте
      const urlObj = new URL(serverUrl.trim());
      if (urlObj.port === '8501') {
        Alert.alert(
          '⚠️ Неправильный порт',
          'Порт 8501 используется для Streamlit (веб-интерфейс).\n\nДля мобильного приложения нужен порт 8000 (FastAPI).\n\nИзмените на: http://' + urlObj.hostname + ':8000',
          [
            { text: 'Отмена', style: 'cancel' },
            {
              text: 'Исправить автоматически',
              onPress: () => {
                const correctedUrl = `http://${urlObj.hostname}:8000`;
                setServerUrl(correctedUrl);
                Alert.alert('Исправлено', `URL изменён на: ${correctedUrl}\n\nНажмите "Сохранить настройки" снова.`);
              },
            },
          ]
        );
        return;
      }

      // Проверка, что используется правильный порт 8000
      if (urlObj.port && urlObj.port !== '8000') {
        Alert.alert(
          '⚠️ Предупреждение',
          `Вы используете порт ${urlObj.port}. Убедитесь, что это правильный порт для FastAPI сервера (обычно 8000).`,
          [
            { text: 'Отмена', style: 'cancel' },
            { text: 'Продолжить', onPress: async () => {
              await saveSettingsConfirmed();
            }},
          ]
        );
        return;
      }

      await saveSettingsConfirmed();
    } catch (error) {
      if (error.message && error.message.includes('Invalid URL')) {
        Alert.alert('Ошибка', 'Неверный формат URL. Используйте формат: http://ip-адрес:порт');
      } else {
        Alert.alert('Ошибка', 'Не удалось сохранить настройки: ' + error.message);
      }
    }
  };

  const saveSettingsConfirmed = async () => {
    try {
      await StorageService.saveSettings({ serverUrl: serverUrl.trim() });
      setSaved(true);
      if (onSettingsChange) {
        onSettingsChange(serverUrl.trim());
      }
      setTimeout(() => setSaved(false), 2000);
      Alert.alert('✅ Успех', 'Настройки сохранены.\n\nДля применения изменений может потребоваться перезапустить приложение.');
    } catch (error) {
      Alert.alert('Ошибка', 'Не удалось сохранить настройки');
    }
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>⚙️ Настройки</Text>
        <Text style={styles.subtitle}>Факультет Искусственного Интеллекта РУДН</Text>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Подключение к серверу</Text>
        <Text style={styles.label}>URL сервера API:</Text>
        <TextInput
          style={styles.input}
          value={serverUrl}
          onChangeText={setServerUrl}
          placeholder="http://your-server-ip:8000"
          autoCapitalize="none"
          autoCorrect={false}
        />
        <Text style={styles.hint}>
          Введите IP адрес вашего сервера (например: http://192.168.1.100:8000)
        </Text>
      </View>

      <TouchableOpacity
        style={[styles.saveButton, saved && styles.savedButton]}
        onPress={saveSettings}
      >
        <Text style={styles.saveButtonText}>
          {saved ? '✅ Сохранено' : 'Сохранить настройки'}
        </Text>
      </TouchableOpacity>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>О приложении</Text>
        <Text style={styles.aboutText}>
          Приложение для распознавания туристических достопримечательностей Северного Кавказа
        </Text>
        <Text style={styles.aboutText}>
          Версия: 1.0.0
        </Text>
        <Text style={styles.aboutText}>
          Факультет Искусственного Интеллекта РУДН
        </Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    backgroundColor: '#667eea',
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
    fontSize: 14,
    color: '#fff',
    opacity: 0.9,
  },
  section: {
    backgroundColor: '#fff',
    margin: 15,
    padding: 15,
    borderRadius: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#2c3e50',
    marginBottom: 15,
  },
  label: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#2c3e50',
    marginBottom: 5,
  },
  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 5,
    padding: 10,
    fontSize: 14,
    backgroundColor: '#fff',
    marginBottom: 5,
  },
  hint: {
    fontSize: 12,
    color: '#999',
    marginTop: 5,
  },
  saveButton: {
    backgroundColor: '#27ae60',
    margin: 15,
    padding: 15,
    borderRadius: 10,
    alignItems: 'center',
  },
  savedButton: {
    backgroundColor: '#2ecc71',
  },
  saveButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  aboutText: {
    fontSize: 14,
    color: '#666',
    lineHeight: 20,
    marginBottom: 10,
  },
});

