import { onBeforeUnmount, onMounted, ref } from '../js/vue/runtime.js';
import { mountVueApp } from '../js/vue/boot.js';
import { useApi } from '../js/vue/composables/useApi.js';
import { HistoryRow } from '../js/vue/components/HistoryRow.js';

mountVueApp('#historyApp', {
  components: { HistoryRow },
  setup() {
    const api = useApi();
    const history = ref([]);
    const loading = ref(false);

    const loadHistory = async () => {
      loading.value = true;
      try {
        const data = await api.getHistory();
        history.value = data.items || [];
      } catch (err) {
        console.error('Failed to load history', err);
      } finally {
        loading.value = false;
      }
    };

    const handleTorrentAdded = () => loadHistory();

    onMounted(() => {
      loadHistory();
      window.addEventListener('torrentAdded', handleTorrentAdded);
    });

    onBeforeUnmount(() => {
      window.removeEventListener('torrentAdded', handleTorrentAdded);
    });

    return { history, loading, loadHistory };
  }
});
