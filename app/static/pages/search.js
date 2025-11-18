import { reactive, ref, watch, onMounted } from '../js/vue/runtime.js';
import { createRouter, createWebHistory, useRoute, useRouter } from '../js/vue/router.js';
import { mountVueApp } from '../js/vue/boot.js';
import { useApi } from '../js/vue/composables/useApi.js';
import { ResultRow } from '../js/vue/components/ResultRow.js';
import { useSharedCoverLoader } from '../js/vue/services/coverLoaderService.js';

const searchPageRouter = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: window.location.pathname || '/',
      component: { template: '<div />' }
    }
  ]
});

const normalizeQuery = (values) => {
  const query = {};
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      query[key] = value;
    }
  });
  return query;
};

mountVueApp('#searchApp', {
  components: { ResultRow },
  setup() {
    const api = useApi();
    const route = useRoute();
    const router = useRouter();
    const form = reactive({ q: '', sort: 'default', perpage: '20' });
    const results = ref([]);
    const status = ref('');
    const loading = ref(false);
    const coverLoader = useSharedCoverLoader();

    const syncForm = () => {
      const getValue = (key, fallback) => {
        const value = route.query[key];
        if (Array.isArray(value)) {
          return value[value.length - 1] ?? fallback;
        }
        return value ?? fallback;
      };

      form.q = getValue('q', '');
      form.sort = getValue('sort', 'default');
      form.perpage = getValue('perpage', '20');
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
        router.replace({
          query: normalizeQuery({ q: form.q.trim(), sort: form.sort, perpage: form.perpage })
        });
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

    watch(() => [route.query.q, route.query.sort, route.query.perpage], () => {
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
}, { router: searchPageRouter });
