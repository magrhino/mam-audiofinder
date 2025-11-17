import { reactive } from '../runtime.js';

export function useUrlRouter(defaultParams = {}) {
  const state = reactive({ ...defaultParams });

  const syncFromUrl = () => {
    const params = new URLSearchParams(window.location.search);
    Object.keys(defaultParams).forEach((key) => {
      state[key] = params.get(key) ?? defaultParams[key];
    });
  };

  const updateUrl = (patch = {}, replace = false) => {
    const params = new URLSearchParams(window.location.search);
    Object.entries({ ...defaultParams, ...patch }).forEach(([key, value]) => {
      if (value === undefined || value === null || value === '') {
        params.delete(key);
      } else {
        params.set(key, value);
      }
    });
    const query = params.toString();
    const newUrl = query ? `${window.location.pathname}?${query}` : window.location.pathname;
    if (replace) {
      window.history.replaceState({}, '', newUrl);
    } else {
      window.history.pushState({}, '', newUrl);
    }
  };

  window.addEventListener('popstate', () => syncFromUrl());
  syncFromUrl();

  return { state, syncFromUrl, updateUrl };
}
