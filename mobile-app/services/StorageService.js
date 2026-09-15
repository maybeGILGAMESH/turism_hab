import AsyncStorage from '@react-native-async-storage/async-storage';

// v3 keys are separate so the stable 2.0 client on the same device keeps its own data.
const HISTORY_KEY = 'v3:recognition_history';
const SETTINGS_KEY = 'v3:app_settings';
const ROUTE_KEY = 'v3:route_state';
const GUIDE_KEY = 'v3:guide_history';
const MAX_GUIDE_TURNS = 30;

async function readJson(key, fallback) {
  try {
    const value = await AsyncStorage.getItem(key);
    return value ? JSON.parse(value) : fallback;
  } catch (error) {
    console.error(`Error reading ${key}:`, error);
    return fallback;
  }
}

async function writeJson(key, value) {
  try {
    await AsyncStorage.setItem(key, JSON.stringify(value));
  } catch (error) {
    console.error(`Error writing ${key}:`, error);
  }
}

export class StorageService {
  /**
   * Сохранить результат распознавания в историю
   */
  static async saveRecognition(result) {
    const history = await this.getHistory();
    const newResult = {
      id: Date.now().toString(),
      ...result,
      timestamp: result.timestamp || new Date().toISOString(),
    };
    history.unshift(newResult);
    await AsyncStorage.setItem(HISTORY_KEY, JSON.stringify(history));
    return newResult.id;
  }

  static async getHistory() {
    return readJson(HISTORY_KEY, []);
  }

  static async deleteFromHistory(resultId) {
    const history = await this.getHistory();
    await writeJson(HISTORY_KEY, history.filter(item => item.id !== resultId));
  }

  static async clearHistory() {
    try {
      await AsyncStorage.removeItem(HISTORY_KEY);
    } catch (error) {
      console.error('Error clearing history:', error);
    }
  }

  static async saveSettings(settings) {
    await writeJson(SETTINGS_KEY, settings);
  }

  static async getSettings() {
    return readJson(SETTINGS_KEY, {});
  }

  static async getRouteState() {
    return readJson(ROUTE_KEY, { routeIds: [], travelMode: 'walk' });
  }

  static async saveRouteState(state) {
    await writeJson(ROUTE_KEY, state);
  }

  /** История диалога с гидом хранится только на устройстве. */
  static async getGuideHistory() {
    return readJson(GUIDE_KEY, []);
  }

  static async saveGuideHistory(turns) {
    await writeJson(GUIDE_KEY, turns.slice(-MAX_GUIDE_TURNS));
  }

  static async clearGuideHistory() {
    try {
      await AsyncStorage.removeItem(GUIDE_KEY);
    } catch (error) {
      console.error('Error clearing guide history:', error);
    }
  }
}
