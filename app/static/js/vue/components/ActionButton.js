import { computed } from '../runtime.js';

export const ActionButton = {
  name: 'ActionButton',
  props: {
    label: { type: String, default: '' },
    variant: { type: String, default: '' },
    disabled: { type: Boolean, default: false },
    loading: { type: Boolean, default: false }
  },
  emits: ['click'],
  setup(props, { emit, slots }) {
    const classes = computed(() => [
      'action-btn',
      props.variant ? `action-btn--${props.variant}` : null,
      props.loading ? 'is-loading' : null
    ].filter(Boolean).join(' '));

    const handleClick = (event) => {
      if (props.disabled || props.loading) return;
      emit('click', event);
    };

    const labelText = computed(() => {
      if (props.loading) return props.label || 'Working…';
      return props.label;
    });

    return { classes, handleClick, labelText, slots };
  },
  template: `
    <button :class="classes" :disabled="disabled || loading" @click="handleClick">
      <slot>{{ labelText }}</slot>
    </button>
  `
};
