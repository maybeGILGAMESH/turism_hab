import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { Api } from '../services/api';
import { StorageService } from '../services/StorageService';

const AppStateContext = createContext(null);

export function AppStateProvider({ apiUrl, children }) {
  const [objects, setObjects] = useState([]);
  const [loadingObjects, setLoadingObjects] = useState(true);
  const [objectsError, setObjectsError] = useState('');
  const [routeIds, setRouteIds] = useState([]);
  const [travelMode, setTravelModeState] = useState('walk');

  useEffect(() => {
    StorageService.getRouteState().then(state => {
      setRouteIds(Array.isArray(state.routeIds) ? state.routeIds : []);
      setTravelModeState(state.travelMode === 'car' ? 'car' : 'walk');
    });
  }, []);

  const reloadObjects = useCallback(async () => {
    setLoadingObjects(true);
    setObjectsError('');
    try {
      setObjects(await Api.objects(apiUrl));
    } catch (error) {
      setObjectsError(error.message);
    } finally {
      setLoadingObjects(false);
    }
  }, [apiUrl]);

  useEffect(() => {
    reloadObjects();
  }, [reloadObjects]);

  const persist = useCallback((ids, mode) => StorageService.saveRouteState({ routeIds: ids, travelMode: mode }), []);

  const toggleRoute = useCallback(id => {
    setRouteIds(previous => {
      const next = previous.includes(id) ? previous.filter(value => value !== id) : [...previous, id].slice(0, 20);
      persist(next, travelMode);
      return next;
    });
  }, [persist, travelMode]);

  const replaceRoute = useCallback(ids => {
    const next = ids.slice(0, 20);
    setRouteIds(next);
    persist(next, travelMode);
  }, [persist, travelMode]);

  const setTravelMode = useCallback(mode => {
    setTravelModeState(mode);
    setRouteIds(previous => {
      persist(previous, mode);
      return previous;
    });
  }, [persist]);

  const value = useMemo(() => ({
    apiUrl,
    objects,
    objectsById: new Map(objects.map(item => [item.id, item])),
    loadingObjects,
    objectsError,
    reloadObjects,
    routeIds,
    toggleRoute,
    replaceRoute,
    clearRoute: () => replaceRoute([]),
    travelMode,
    setTravelMode,
  }), [apiUrl, objects, loadingObjects, objectsError, reloadObjects, routeIds, toggleRoute, replaceRoute, travelMode, setTravelMode]);

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
}

export function useAppState() {
  const value = useContext(AppStateContext);
  if (!value) throw new Error('useAppState must be used inside AppStateProvider');
  return value;
}
