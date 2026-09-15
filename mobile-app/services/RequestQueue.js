import AsyncStorage from '@react-native-async-storage/async-storage';
import NetInfo from '@react-native-community/netinfo';
import { StorageService } from './StorageService';

const QUEUE_KEY = 'v3:request_queue';
const MAX_RETRIES = 3;

export class RequestQueue {
  /**
   * Добавить запрос в очередь
   */
  static async addToQueue(request) {
    try {
      const queue = await this.getQueue();
      const newRequest = {
        id: Date.now().toString(),
        ...request,
        retries: 0,
        createdAt: new Date().toISOString(),
      };
      queue.push(newRequest);
      await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
      return newRequest.id;
    } catch (error) {
      console.error('Error adding to queue:', error);
      throw error;
    }
  }

  /**
   * Получить очередь запросов
   */
  static async getQueue() {
    try {
      const queueJson = await AsyncStorage.getItem(QUEUE_KEY);
      return queueJson ? JSON.parse(queueJson) : [];
    } catch (error) {
      console.error('Error getting queue:', error);
      return [];
    }
  }

  /**
   * Получить количество запросов в очереди
   */
  static async getQueueLength() {
    const queue = await this.getQueue();
    return queue.length;
  }

  /**
   * Удалить запрос из очереди
   */
  static async removeFromQueue(requestId) {
    try {
      const queue = await this.getQueue();
      const filteredQueue = queue.filter(req => req.id !== requestId);
      await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(filteredQueue));
    } catch (error) {
      console.error('Error removing from queue:', error);
    }
  }

  /**
   * Обработать очередь запросов
   */
  static async processQueue(apiBaseUrl) {
    console.log('🔄 Starting queue processing, API URL:', apiBaseUrl);
    
    if (!apiBaseUrl) {
      console.error('❌ API base URL is not provided, skipping queue processing');
      return;
    }

    const isConnected = await NetInfo.fetch().then(state => state.isConnected);
    if (!isConnected) {
      console.log('⚠️ No internet connection, skipping queue processing');
      return;
    }

    console.log('✅ Internet connection available');

    // Проверяем доступность сервера перед обработкой
    try {
      const healthController = new AbortController();
      const healthTimeout = setTimeout(() => healthController.abort(), 5000);
      const healthCheck = await fetch(`${apiBaseUrl}/health`, {
        method: 'GET',
        signal: healthController.signal,
      });
      clearTimeout(healthTimeout);
      if (!healthCheck.ok) {
        console.warn('⚠️ Server health check failed, but continuing...');
      } else {
        console.log('✅ Server is healthy and reachable');
      }
    } catch (healthError) {
      console.error('❌ Server is not reachable:', healthError.message);
      console.error('   URL:', `${apiBaseUrl}/health`);
      console.warn('⚠️ Skipping queue processing - server unavailable');
      return;
    }

    const queue = await this.getQueue();
    if (queue.length === 0) {
      console.log('📭 Queue is empty');
      return;
    }

    console.log(`📋 Processing ${queue.length} request(s) from queue`);

    for (const request of queue) {
      try {
        console.log(`🔄 Processing request ${request.id} (attempt ${(request.retries || 0) + 1})`);
        await this.processRequest(request, apiBaseUrl);
      } catch (error) {
        console.error(`❌ Error processing request ${request.id}:`, error);
        console.error('   Error type:', error.name);
        console.error('   Error message:', error.message);
        if (error.stack) {
          console.error('   Stack:', error.stack);
        }
        
        // Увеличиваем счетчик попыток
        request.retries = (request.retries || 0) + 1;
        console.log(`   Retry count: ${request.retries}/${MAX_RETRIES}`);
        
        if (request.retries >= MAX_RETRIES) {
          // Удаляем запрос после максимального количества попыток
          await this.removeFromQueue(request.id);
          console.log(`🗑️ Request ${request.id} removed after ${MAX_RETRIES} retries`);
        } else {
          // Обновляем запрос с новым счетчиком попыток
          await this.updateRequest(request);
          console.log(`📝 Request ${request.id} updated, will retry later`);
        }
      }
    }
  }

  /**
   * Обработать один запрос
   */
  static async processRequest(request, apiBaseUrl) {
    const { type, data, imageUri } = request;

    if (!apiBaseUrl) {
      throw new Error('API base URL is required');
    }

    if (!imageUri) {
      throw new Error('Image URI is required for recognition request');
    }

    if (type === 'recognize') {
      console.log(`📤 Sending recognition request ${request.id} to: ${apiBaseUrl}/api/recognize`);
      console.log(`   Image URI: ${imageUri}`);

      // Формируем FormData для отправки изображения
      const formData = new FormData();
      formData.append('file', {
        uri: imageUri,
        type: 'image/jpeg',
        name: 'photo.jpg',
      });

      console.log('📋 FormData created, sending request...');

      // Создаем AbortController для таймаута (90 секунд для очереди)
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 90000);

      try {
        const response = await fetch(`${apiBaseUrl}/api/recognize`, {
          method: 'POST',
          body: formData,
          signal: controller.signal,
          // НЕ устанавливаем Content-Type вручную - React Native установит его автоматически
        });

        clearTimeout(timeoutId);

        console.log(`📥 Response received for request ${request.id}, status: ${response.status}`);

        if (!response.ok) {
          let errorText = '';
          try {
            errorText = await response.text();
          } catch (e) {
            errorText = 'Could not read error message';
          }
          console.error(`❌ HTTP error for request ${request.id}:`, response.status, errorText);
          throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
        }

        const result = await response.json();
        console.log(`✅ Request ${request.id} processed successfully`);
        console.log(`   Result:`, result);
      
        // Сохраняем результат в историю
        await StorageService.saveRecognition({
          ...result,
          imageUri,
          timestamp: new Date().toISOString(),
          requestId: request.id,
        });

        // Удаляем запрос из очереди после успешной обработки
        await this.removeFromQueue(request.id);
        console.log(`🗑️ Request ${request.id} removed from queue`);
      } catch (fetchError) {
        clearTimeout(timeoutId);
        
        if (fetchError.name === 'AbortError') {
          console.error(`⏱️ Request ${request.id} timeout after 90 seconds`);
          throw new Error('Request timeout after 90 seconds');
        }
        
        // Более подробная обработка сетевых ошибок
        if (fetchError.message && fetchError.message.includes('Network request failed')) {
          console.error(`🌐 Network error for request ${request.id}:`);
          console.error(`   URL: ${apiBaseUrl}/api/recognize`);
          console.error(`   Possible causes:`);
          console.error(`   - Server is not running`);
          console.error(`   - Incorrect URL in settings`);
          console.error(`   - Network connectivity issue`);
          console.error(`   - Firewall blocking the connection`);
          throw new Error(`Network request failed: Cannot reach server at ${apiBaseUrl}. Please check server status and URL in settings.`);
        }
        
        throw fetchError;
      }
    } else {
      throw new Error(`Unknown request type: ${type}`);
    }
  }

  /**
   * Обновить запрос в очереди
   */
  static async updateRequest(updatedRequest) {
    try {
      const queue = await this.getQueue();
      const index = queue.findIndex(req => req.id === updatedRequest.id);
      if (index !== -1) {
        queue[index] = updatedRequest;
        await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
      }
    } catch (error) {
      console.error('Error updating request:', error);
    }
  }

  /**
   * Очистить очередь
   */
  static async clearQueue() {
    try {
      await AsyncStorage.removeItem(QUEUE_KEY);
    } catch (error) {
      console.error('Error clearing queue:', error);
    }
  }
}

