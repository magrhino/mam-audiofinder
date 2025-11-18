import { computed, onMounted } from '../runtime.js';
import { useCover } from '../composables/useCovers.js';
import { useLibraryCheck } from '../composables/useLibraryCheck.js';

export const ShowcaseCard = {
  name: 'ShowcaseCard',
  props: {
    group: { type: Object, required: true }
  },
  emits: ['select'],
  setup(props, { emit }) {
    // Use composables for cover loading and library check
    const { coverUrl, loading: loadingCover, error: coverError, fetchCover } = useCover({
      mamId: props.group.mam_id,
      title: props.group.display_title,
      author: props.group.author || ''
    });

    const { inLibrary, indicatorConfig } = useLibraryCheck(computed(() => props.group));

    // Load cover on mount if not already provided
    onMounted(() => {
      if (props.group.cover_url) {
        coverUrl.value = props.group.cover_url;
        loadingCover.value = false;
      } else {
        fetchCover();
      }
    });

    const versionsLabel = computed(() => {
      const total = props.group.total_versions || 0;
      return `${total} version${total === 1 ? '' : 's'}`;
    });

    const handleClick = () => emit('select', props.group);

    return {
      coverUrl,
      loadingCover,
      coverError,
      inLibrary,
      indicatorConfig,
      versionsLabel,
      handleClick
    };
  },
  template: `
    <div class="showcase-card" @click="handleClick">
      <div class="showcase-versions-badge">{{ versionsLabel }}</div>
      <div class="showcase-cover-skeleton" v-if="loadingCover">
        <span v-if="indicatorConfig"
              :class="indicatorConfig.className"
              :title="indicatorConfig.title"
              :aria-label="indicatorConfig.ariaLabel">
          {{ indicatorConfig.symbol }}
        </span>
      </div>
      <div class="showcase-cover-wrapper" v-else>
        <img v-if="coverUrl" class="showcase-cover" :src="coverUrl" :alt="group.display_title" loading="lazy" />
        <div v-else-if="coverError" class="showcase-cover-placeholder">{{ coverError }}</div>
        <div v-else class="showcase-cover-placeholder">📚</div>
        <span v-if="indicatorConfig"
              :class="indicatorConfig.className"
              :title="indicatorConfig.title"
              :aria-label="indicatorConfig.ariaLabel">
          {{ indicatorConfig.symbol }}
        </span>
      </div>
      <div class="showcase-title">{{ group.display_title }}</div>
      <div class="showcase-author">{{ group.author }}</div>
      <div class="showcase-formats">
        <span v-for="format in group.formats || []" :key="format" class="showcase-format-badge">{{ format }}</span>
      </div>
    </div>
  `
};
