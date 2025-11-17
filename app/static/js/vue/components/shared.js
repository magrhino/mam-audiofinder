import { ActionButton } from './ActionButton.js';
import { StatusBadge } from './StatusBadge.js';

export function registerSharedComponents(app) {
  app.component('ActionButton', ActionButton);
  app.component('StatusBadge', StatusBadge);
}
