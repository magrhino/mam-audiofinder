import { createApp } from './runtime.js';
import { registerSharedComponents } from './components/shared.js';

export function mountVueApp(rootSelector, component) {
  const root = typeof rootSelector === 'string' ? document.querySelector(rootSelector) : rootSelector;
  if (!root) {
    console.warn(`[VueBoot] Unable to find root element for selector ${rootSelector}`);
    return null;
  }

  const app = createApp(component);
  registerSharedComponents(app);
  app.mount(root);
  return app;
}
