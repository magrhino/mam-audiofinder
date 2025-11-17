import { computed, onMounted, ref } from '../runtime.js';
import { useApi } from '../composables/useApi.js';

export const ShowcaseCard = {
  name: 'ShowcaseCard',
  props: {
    group: { type: Object, required: true }
  },
  emits: ['select'],
  setup(props, { emit }) {
    const api = useApi();
    const coverUrl = ref('');
    const loadingCover = ref(true);

    const loadCover = async () => {
      loadingCover.value = true;
      try {
        if (props.group.cover_url) {
          coverUrl.value = props.group.cover_url;
        } else if (props.group.mam_id && props.group.display_title) {
          const data = await api.fetchCover({
            mam_id: props.group.mam_id,
            title: props.group.display_title,
            author: props.group.author || '',
            max_retries: '2'
          });
          coverUrl.value = data.cover_url || '';
        }
      } catch (err) {
        console.warn('Cover load failed', err);
      } finally {
        loadingCover.value = false;
      }
    };

    onMounted(loadCover);

    const versionsLabel = computed(() => {
      const total = props.group.total_versions || 0;
      return `${total} version${total === 1 ? '' : 's'}`;
    });

    const handleClick = () => emit('select', props.group);

    return { coverUrl, loadingCover, versionsLabel, handleClick };
  },
  template: `
    <div class="showcase-card" @click="handleClick">
      <div class="showcase-versions-badge">{{ versionsLabel }}</div>
      <div class="showcase-cover-skeleton" v-if="loadingCover">
        <span v-if="group.in_abs_library" class="in-library-indicator" title="Already in your library">✓</span>
      </div>
      <div class="showcase-cover-wrapper" v-else>
        <img v-if="coverUrl" class="showcase-cover" :src="coverUrl" :alt="group.display_title" loading="lazy" />
        <div v-else class="showcase-cover-placeholder">📚</div>
        <span v-if="group.in_abs_library" class="in-library-indicator" title="Already in your library">✓</span>
      </div>
      <div class="showcase-title">{{ group.display_title }}</div>
      <div class="showcase-author">{{ group.author }}</div>
      <div class="showcase-formats">
        <span v-for="format in group.formats || []" :key="format" class="showcase-format-badge">{{ format }}</span>
      </div>
    </div>
  `
};
