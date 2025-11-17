import { computed, onMounted, reactive, ref, watch } from '../runtime.js';
import { formatSize } from '../../core/utils.js';
import { useSharedCoverLoader } from '../services/coverLoaderService.js';

let rowCounter = 0;

export const ResultRow = {
  name: 'ResultRow',
  props: {
    item: { type: Object, required: true }
  },
  emits: ['add'],
  setup(props, { emit }) {
    const coverEl = ref(null);
    const loader = useSharedCoverLoader();
    const rowId = `result-row-${rowCounter++}`;
    const rowState = reactive({ ...props.item });

    const observe = () => {
      const el = coverEl.value;
      if (!el) return;
      el.className = 'cover-skeleton';
      el.innerHTML = '';
      el.dataset.mamId = props.item?.id || '';
      el.dataset.title = props.item?.title || '';
      el.dataset.author = props.item?.author_info || '';
      el.dataset.rowId = rowId;
      loader.setRowState(rowId, rowState);
      loader.init();
      loader.observe(el);
    };

    onMounted(() => {
      observe();
    });

    watch(() => props.item, (val) => {
      Object.assign(rowState, val || {});
      observe();
    }, { deep: true });

    const seeders = computed(() => {
      const s = props.item?.seeders ?? '-';
      const l = props.item?.leechers ?? '-';
      return `${s} / ${l}`;
    });

    const detailsUrl = computed(() => props.item?.id ? `https://www.myanonamouse.net/t/${encodeURIComponent(props.item.id)}` : '');
    const isAddDisabled = computed(() => !(props.item?.dl || props.item?.id));

    const handleAdd = () => {
      emit('add', { ...rowState });
    };

    return { coverEl, seeders, detailsUrl, isAddDisabled, handleAdd, formatSize };
  },
  template: `
    <tr>
      <td style="padding:0.25rem;">
        <div ref="coverEl" class="cover-skeleton">
          <span v-if="item.in_abs_library" class="in-library-indicator" title="Already in your library">✓</span>
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
        <ActionButton label="Add" variant="primary" :disabled="isAddDisabled" @click="handleAdd" />
      </td>
    </tr>
  `
};
