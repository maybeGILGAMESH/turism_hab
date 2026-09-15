import { Platform } from 'react-native';

export const APP_VERSION = '3.0.0';
export const API_PORT = 8100;
export const STREAMLIT_PORT = 8601;

export const DEFAULT_API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL ||
  (Platform.OS === 'android' ? `http://10.0.2.2:${API_PORT}` : `http://localhost:${API_PORT}`);
