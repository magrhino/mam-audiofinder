export const StatusBadge = {
  name: 'StatusBadge',
  props: {
    label: { type: String, required: true },
    variant: { type: String, default: 'muted' },
    title: { type: String, default: '' }
  },
  template: `
    <span class="status-badge" :class="`status-badge--${variant}`" :title="title">{{ label }}</span>
  `
};
