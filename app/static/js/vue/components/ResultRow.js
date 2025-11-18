import { computed, ref } from '../runtime.js';
import { formatSize } from '../../core/utils.js';
import { useLazyCover } from '../composables/useCovers.js';
import { useLibraryCheck } from '../composables/useLibraryCheck.js';
import { useAddAction } from '../composables/useActionButtons.js';

export const ResultRow = {
  name: 'ResultRow',
  props: {
    item: { type: Object, required: true }
  },
  emits: ['add'],
  setup(props, { emit }) {
    const coverEl = ref(null);

    // Use composables for cover loading, library check, and add action
    const { coverUrl, loading: coverLoading, error: coverError } = useLazyCover({
      mamId: computed(() => props.item?.id || ''),
      title: computed(() => props.item?.title || ''),
      author: computed(() => props.item?.author_info || ''),
      elementRef: coverEl
    });

    const { inLibrary, indicatorConfig } = useLibraryCheck(computed(() => props.item));
    const { adding, performAdd, canAdd } = useAddAction(computed(() => props.item));

    // Computed properties
    const seeders = computed(() => {
      const s = props.item?.seeders ?? '-';
      const l = props.item?.leechers ?? '-';
      return `${s} / ${l}`;
    });

    const detailsUrl = computed(() =>
      props.item?.id ? `https://www.myanonamouse.net/t/${encodeURIComponent(props.item.id)}` : ''
    );

    const isAddDisabled = computed(() => !canAdd.value || adding.value);

    const handleAdd = async () => {
      const result = await performAdd();
      if (result.success) {
        emit('add', props.item);
      }
    };

    return {
      coverEl,
      coverUrl,
      coverLoading,
      coverError,
      inLibrary,
      indicatorConfig,
      seeders,
      detailsUrl,
      isAddDisabled,
      adding,
      handleAdd,
      formatSize
    };
  },
  template: `
    <tr>
      <td style="padding:0.25rem;">
        <div ref="coverEl" class="cover-skeleton" :class="{ 'cover-loaded': coverUrl }">
          <img v-if="coverUrl" :src="coverUrl" alt="Cover" class="cover-image loaded" />
          <div v-else-if="coverError" class="cover-placeholder">{{ coverError }}</div>
          <span v-if="indicatorConfig"
                :class="indicatorConfig.className"
                :title="indicatorConfig.title"
                :aria-label="indicatorConfig.ariaLabel">
            {{ indicatorConfig.symbol }}
          </span>
        </div>
      </td>
      <td>{{ item.title }}</td>
      <td>{{ item.author_info }}</td>
      <td>{{ item.narrator_info }}</td>
      <td>{{ item.format }}</td>
      <td class="right">{{ formatSize(item.size) }}</td>
      <td class="right">{{ seeders }}</td>
      <td>{{ item.added }}</td>
      <td class="center">
        <a v-if="detailsUrl" :href="detailsUrl" target="_blank" rel="noopener">🔗</a>
      </td>
      <td>
        <ActionButton
          :label="adding ? 'Adding…' : 'Add'"
          variant="primary"
          :disabled="isAddDisabled"
          @click="handleAdd" />
      </td>
    </tr>
  `
};
