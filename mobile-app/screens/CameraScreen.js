import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Image,
  Alert,
  ActivityIndicator,
  ScrollView,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import NetInfo from '@react-native-community/netinfo';
import { RequestQueue } from '../services/RequestQueue';
import { StorageService } from '../services/StorageService';

export default function CameraScreen({ isConnected, apiUrl: defaultApiUrl, onQueueUpdate }) {
  const [image, setImage] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [apiUrl, setApiUrl] = useState(defaultApiUrl);

  useEffect(() => {
    // Загружаем сохраненный URL сервера из настроек
    const loadApiUrl = async () => {
      try {
        const settings = await StorageService.getSettings();
        if (settings.serverUrl) {
          setApiUrl(settings.serverUrl);
        }
      } catch (error) {
        console.error('Error loading API URL:', error);
      }
    };
    loadApiUrl();
  }, []);

  const pickImage = async () => {
    // Запрашиваем разрешение на доступ к камере/галерее
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Ошибка', 'Необходимо разрешение на доступ к галерее');
      return;
    }

    // Открываем галерею
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      aspect: [4, 3],
      quality: 0.8,
    });

    if (!result.canceled) {
      setImage(result.assets[0].uri);
      setResult(null);
    }
  };

  const takePhoto = async () => {
    // Запрашиваем разрешение на доступ к камере
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Ошибка', 'Необходимо разрешение на доступ к камере');
      return;
    }

    // Открываем камеру
    const result = await ImagePicker.launchCameraAsync({
      allowsEditing: true,
      aspect: [4, 3],
      quality: 0.8,
    });

    if (!result.canceled) {
      setImage(result.assets[0].uri);
      setResult(null);
    }
  };

  const recognizeImage = async () => {
    if (!image) {
      Alert.alert('Ошибка', 'Пожалуйста, выберите изображение');
      return;
    }

    setLoading(true);
    setResult(null);

    const isConnectedNow = await NetInfo.fetch().then(state => state.isConnected);

    if (!isConnectedNow) {
      // Нет интернета - сохраняем в очередь
      try {
        await RequestQueue.addToQueue({
          type: 'recognize',
          imageUri: image,
          data: {},
        });
        Alert.alert(
          'Офлайн режим',
          'Изображение добавлено в очередь. Распознавание будет выполнено при наличии интернета.',
          [{ text: 'OK', onPress: () => onQueueUpdate() }]
        );
      } catch (error) {
        Alert.alert('Ошибка', 'Не удалось добавить запрос в очередь');
      }
      setLoading(false);
      return;
    }

    // Есть интернет - отправляем запрос сразу
    try {
      console.log('📤 Starting recognition request to:', `${apiUrl}/api/recognize`);
      console.log('📷 Image URI:', image);
      
      // Проверяем доступность сервера (опционально)
      try {
        const healthController = new AbortController();
        const healthTimeout = setTimeout(() => healthController.abort(), 5000);
        const healthCheck = await fetch(`${apiUrl}/health`, {
          method: 'GET',
          signal: healthController.signal,
        });
        clearTimeout(healthTimeout);
        if (!healthCheck.ok) {
          console.warn('⚠️ Server health check failed, but continuing...');
        } else {
          console.log('✅ Server is healthy');
        }
      } catch (healthError) {
        console.warn('⚠️ Could not check server health:', healthError.message);
        // Продолжаем запрос, даже если health check не прошел
      }
      
      const formData = new FormData();
      formData.append('file', {
        uri: image,
        type: 'image/jpeg',
        name: 'photo.jpg',
      });

      console.log('📋 FormData created, sending request...');

      // Создаем AbortController для таймаута
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 60000); // 60 секунд таймаут

      try {
        const response = await fetch(`${apiUrl}/api/recognize`, {
          method: 'POST',
          body: formData,
          signal: controller.signal,
          // НЕ устанавливаем Content-Type вручную - браузер/React Native установит его автоматически
          // с правильным boundary для multipart/form-data
        });

        clearTimeout(timeoutId);

        console.log('📥 Response received, status:', response.status);

        if (!response.ok) {
          const errorText = await response.text();
          console.error('❌ HTTP error:', response.status, errorText);
          throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
        }

        const recognitionResult = await response.json();
        console.log('✅ Recognition result:', recognitionResult);
        setResult(recognitionResult);

        // Сохраняем результат в историю
        await StorageService.saveRecognition({
          ...recognitionResult,
          imageUri: image,
          timestamp: new Date().toISOString(),
        });
      } catch (fetchError) {
        clearTimeout(timeoutId);
        if (fetchError.name === 'AbortError') {
          console.error('⏱️ Request timeout after 60 seconds');
          throw new Error('Превышено время ожидания ответа (60 секунд). Сервер обрабатывает запрос слишком долго.');
        }
        throw fetchError;
      }
    } catch (error) {
      console.error('❌ Recognition error:', error);
      console.error('Error details:', {
        message: error.message,
        name: error.name,
        stack: error.stack,
      });
      
      const errorMessage = error.message || 'Не удалось распознать изображение';
      Alert.alert(
        'Ошибка',
        errorMessage + '\n\nПопробуйте еще раз или добавьте в очередь для обработки позже.'
      );
      
      // Если ошибка, тоже добавляем в очередь для повторной попытки
      try {
        await RequestQueue.addToQueue({
          type: 'recognize',
          imageUri: image,
          data: {},
        });
        onQueueUpdate();
      } catch (queueError) {
        console.error('Error adding to queue:', queueError);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>🏔️ Северный Кавказ</Text>
        <Text style={styles.subtitle}>Распознавание туристических достопримечательностей</Text>
        <Text style={styles.organization}>Факультет Искусственного Интеллекта РУДН</Text>
        {!isConnected && (
          <View style={styles.offlineBanner}>
            <Text style={styles.offlineText}>⚠️ Офлайн режим</Text>
          </View>
        )}
      </View>

      <View style={styles.imageContainer}>
        {image ? (
          <Image source={{ uri: image }} style={styles.image} />
        ) : (
          <View style={styles.placeholder}>
            <Text style={styles.placeholderText}>Выберите изображение</Text>
          </View>
        )}
      </View>

      <View style={styles.buttonContainer}>
        <TouchableOpacity style={styles.button} onPress={pickImage}>
          <Text style={styles.buttonText}>📁 Выбрать из галереи</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.button} onPress={takePhoto}>
          <Text style={styles.buttonText}>📷 Сделать фото</Text>
        </TouchableOpacity>

        {image && (
          <TouchableOpacity
            style={[styles.button, styles.recognizeButton, loading && styles.buttonDisabled]}
            onPress={recognizeImage}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.buttonText}>🔍 Распознать</Text>
            )}
          </TouchableOpacity>
        )}
      </View>

      {result && (
        <View style={styles.resultContainer}>
          <Text style={styles.resultTitle}>Результаты распознавания</Text>
          {result.success ? (
            <View style={styles.successResult}>
              <Text style={styles.successText}>✅ Достопримечательность распознана!</Text>
              <Text style={styles.resultLabel}>ID объекта:</Text>
              <Text style={styles.resultValue}>{result.object_id}</Text>
              <Text style={styles.resultLabel}>Уверенность:</Text>
              <Text style={styles.resultValue}>
                {(result.confidence * 100).toFixed(1)}%
              </Text>
              <Text style={styles.resultLabel}>Описание:</Text>
              <Text style={styles.resultDescription}>{result.description}</Text>
            </View>
          ) : (
            <View style={styles.errorResult}>
              <Text style={styles.errorText}>⚠️ Достопримечательность не распознана</Text>
              <Text style={styles.resultDescription}>{result.message}</Text>
            </View>
          )}
        </View>
      )}
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
    alignItems: 'center',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 5,
  },
  subtitle: {
    fontSize: 16,
    color: '#fff',
    textAlign: 'center',
    marginBottom: 5,
  },
  organization: {
    fontSize: 12,
    color: '#fff',
    opacity: 0.9,
  },
  offlineBanner: {
    marginTop: 10,
    backgroundColor: '#f39c12',
    padding: 8,
    borderRadius: 5,
  },
  offlineText: {
    color: '#fff',
    fontWeight: 'bold',
  },
  imageContainer: {
    margin: 20,
    height: 300,
    backgroundColor: '#fff',
    borderRadius: 10,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  image: {
    width: '100%',
    height: '100%',
    resizeMode: 'cover',
  },
  placeholder: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  placeholderText: {
    fontSize: 16,
    color: '#999',
  },
  buttonContainer: {
    padding: 20,
  },
  button: {
    backgroundColor: '#667eea',
    padding: 15,
    borderRadius: 10,
    marginBottom: 10,
    alignItems: 'center',
  },
  recognizeButton: {
    backgroundColor: '#27ae60',
    marginTop: 10,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  resultContainer: {
    margin: 20,
    padding: 15,
    backgroundColor: '#fff',
    borderRadius: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  resultTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 15,
    color: '#2c3e50',
  },
  successResult: {
    padding: 10,
    backgroundColor: '#d4edda',
    borderRadius: 5,
  },
  successText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#155724',
    marginBottom: 10,
  },
  errorResult: {
    padding: 10,
    backgroundColor: '#f8d7da',
    borderRadius: 5,
  },
  errorText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#721c24',
    marginBottom: 10,
  },
  resultLabel: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#2c3e50',
    marginTop: 10,
  },
  resultValue: {
    fontSize: 14,
    color: '#666',
    marginBottom: 5,
  },
  resultDescription: {
    fontSize: 14,
    color: '#666',
    lineHeight: 20,
    marginTop: 5,
  },
});

