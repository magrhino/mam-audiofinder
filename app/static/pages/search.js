import { reactive, ref, watch, onMounted } from '../js/vue/runtime.js';
import { mountVueApp } from '../js/vue/boot.js';
import { useApi } from '../js/vue/composables/useApi.js';
import { useUrlRouter } from '../js/vue/composables/useUrlRouter.js';
import { ResultRow } from '../js/vue/components/ResultRow.js';
import { useSharedCoverLoader } from '../js/vue/services/coverLoaderService.js';

mountVueApp('#searchApp', {
  components: { ResultRow },
  setup() {
    const api = useApi();
    const router = useUrlRouter({ q: '', sort: 'default', perpage: '20' });
    const form = reactive({ q: '', sort: 'default', perpage: '20' });
    const results = ref([]);
    const status = ref('');
    const loading = ref(false);
    const coverLoader = useSharedCoverLoader();

    const syncForm = () => {
      form.q = router.state.q || '';
      form.sort = router.state.sort || 'default';
      form.perpage = router.state.perpage || '20';
    };

    const runSearch = async (silent = false) => {
      if (!form.q.trim()) {
        status.value = 'Enter a search query to get started.';
        results.value = [];
        return;
      }
      loading.value = true;
      status.value = silent ? status.value : 'Searching…';
      results.value = [];
      coverLoader.clearRowState();
      try {
        const data = await api.search({
          tor: { text: form.q.trim(), sortType: form.sort },
          perpage: parseInt(form.perpage, 10)
        });
        results.value = data.results || [];
        status.value = results.value.length ? `${results.value.length} results shown` : 'No results.';
        router.updateUrl({ q: form.q.trim(), sort: form.sort, perpage: form.perpage }, true);
      } catch (err) {
        console.error('Search failed', err);
        status.value = `Search failed: ${err.message}`;
      } finally {
        loading.value = false;
      }
    };

    const addTorrent = async (rowState) => {
      try {
        await api.addTorrent({
          id: String(rowState.id ?? ''),
          title: rowState.title || '',
          dl: rowState.dl || '',
          author: rowState.author_info || '',
          narrator: rowState.narrator_info || '',
          abs_cover_url: rowState.abs_cover_url || '',
          abs_item_id: rowState.abs_item_id || ''
        });
        status.value = '✓ Added to qBittorrent';
        window.dispatchEvent(new CustomEvent('torrentAdded'));
      } catch (err) {
        status.value = `Add failed: ${err.message}`;
      }
    };

    onMounted(() => {
      syncForm();
      if (form.q) {
        runSearch(true);
      }
    });

    watch(() => [router.state.q, router.state.sort, router.state.perpage], () => {
      const previousQuery = form.q;
      syncForm();
      if (form.q && form.q !== previousQuery) {
        runSearch(true);
      }
      if (!form.q) {
        results.value = [];
        status.value = '';
      }
    });

    return { form, results, status, loading, runSearch, addTorrent };
  }
});
