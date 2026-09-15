const JSON_HEADERS = { 'Content-Type': 'application/json' };

async function request(apiUrl, path, options = {}, timeoutMs = 20000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${apiUrl}${path}`, { ...options, signal: controller.signal });
    let data = null;
    try {
      data = await response.json();
    } catch (error) {
      data = null;
    }
    if (!response.ok) {
      const detail = data && data.detail;
      if (typeof detail === 'string') throw new Error(detail);
      if (response.status === 422) throw new Error('Проверьте введённые данные');
      throw new Error(`Ошибка сервера (${response.status})`);
    }
    return data;
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('Сервер не ответил вовремя. Проверьте подключение.');
    if (error.message === 'Network request failed' || error.message === 'Failed to fetch') {
      throw new Error('Сервер недоступен. Проверьте адрес API в настройках.');
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

export const Api = {
  objects: apiUrl => request(apiUrl, '/api/objects').then(data => data.objects || []),
  object: (apiUrl, id) => request(apiUrl, `/api/objects/${id}`).then(data => data.object),
  planRoute: (apiUrl, body) =>
    request(apiUrl, '/api/plan-route', { method: 'POST', headers: JSON_HEADERS, body: JSON.stringify(body) }),
  chat: (apiUrl, body) =>
    request(apiUrl, '/api/assistant/chat', { method: 'POST', headers: JSON_HEADERS, body: JSON.stringify(body) }, 35000),
  assistantStatus: apiUrl => request(apiUrl, '/api/assistant/status', {}, 6000),
};

export function imageUrl(apiUrl, path) {
  return path ? `${apiUrl}${path}` : null;
}
