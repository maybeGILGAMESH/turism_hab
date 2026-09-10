import AsyncStorage from '@react-native-async-storage/async-storage';

const HISTORY_KEY = 'recognition_history';
const SETTINGS_KEY = 'app_settings';

export class StorageService {
  /**
   * Сохранить результат распознавания в историю
   */
  static async saveRecognition(result) {
    try {
      const history = await this.getHistory();
      const newResult = {
        id: Date.now().toString(),
        ...result,
        timestamp: result.timestamp || new Date().toISOString(),
      };
      history.unshift(newResult); // Добавляем в начало списка
      await AsyncStorage.setItem(HISTORY_KEY, JSON.stringify(history));
      return newResult.id;
    } catch (error) {
      console.error('Error saving recognition:', error);
      throw error;
    }
  }

  /**
   * Получить историю распознаваний
   */
  static async getHistory() {
    try {
      const historyJson = await AsyncStorage.getItem(HISTORY_KEY);
      return historyJson ? JSON.parse(historyJson) : [];
    } catch (error) {
      console.error('Error getting history:', error);
      return [];
    }
  }

  /**
   * Удалить запись из истории
   */
  static async deleteFromHistory(resultId) {
    try {
      const history = await this.getHistory();
      const filteredHistory = history.filter(item => item.id !== resultId);
      await AsyncStorage.setItem(HISTORY_KEY, JSON.stringify(filteredHistory));
    } catch (error) {
      console.error('Error deleting from history:', error);
    }
  }

  /**
   * Очистить историю
   */
  static async clearHistory() {
    try {
      await AsyncStorage.removeItem(HISTORY_KEY);
    } catch (error) {
      console.error('Error clearing history:', error);
    }
  }

  /**
   * Сохранить настройки приложения
   */
  static async saveSettings(settings) {
    try {
      await AsyncStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
    } catch (error) {
      console.error('Error saving settings:', error);
    }
  }

  /**
   * Получить настройки приложения
   */
  static async getSettings() {
    try {
      const settingsJson = await AsyncStorage.getItem(SETTINGS_KEY);
      return settingsJson ? JSON.parse(settingsJson) : {};
    } catch (error) {
      console.error('Error getting settings:', error);
      return {};
    }
  }
}

