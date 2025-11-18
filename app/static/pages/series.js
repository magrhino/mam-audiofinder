import { onMounted, reactive, ref, watch } from '../js/vue/runtime.js';
import { createRouter, createWebHistory, useRoute, useRouter } from '../js/vue/router.js';
import { mountVueApp } from '../js/vue/boot.js';
import { useApi } from '../js/vue/composables/useApi.js';
import { SeriesTable } from '../js/vue/components/SeriesTable.js';

const seriesPageRouter = createRouter({
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

mountVueApp('#seriesApp', {
  components: { SeriesTable },
  setup() {
    const api = useApi();
    const route = useRoute();
    const router = useRouter();
    const form = reactive({ title: '', author: '', limit: '20' });
    const status = ref('Search for a title to see matching series.');
    const results = ref([]);
    const detail = ref(null);

    const syncForm = () => {
      const getValue = (key, fallback) => {
        const value = route.query[key];
        if (Array.isArray(value)) {
          return value[value.length - 1] ?? fallback;
        }
        return value ?? fallback;
      };

      form.title = getValue('title', '');
      form.author = getValue('author', '');
      form.limit = getValue('limit', '20');
    };

    const runSearch = async () => {
      if (!form.title.trim()) {
        status.value = 'Please enter a book title.';
        results.value = [];
        detail.value = null;
        return;
      }
      status.value = 'Searching for series…';
      detail.value = null;
      try {
        const data = await api.searchSeries({
          title: form.title.trim(),
          author: form.author.trim(),
          limit: parseInt(form.limit, 10)
        });
        results.value = data.hardcover_series || [];
        status.value = results.value.length ? `Found ${results.value.length} series` : 'No series found.';
        router.replace({
          query: normalizeQuery({
            title: form.title.trim(),
            author: form.author.trim(),
            limit: form.limit
          })
        });
      } catch (err) {
        status.value = `Series search failed: ${err.message}`;
      }
    };

    const loadDetail = async (series) => {
      status.value = 'Loading series books…';
      try {
        const data = await api.getSeriesBooks(series.series_id);
        detail.value = data;
        status.value = `${data.books?.length || 0} books in this series`;
      } catch (err) {
        status.value = `Failed to load series: ${err.message}`;
      }
    };

    onMounted(() => {
      syncForm();
      if (form.title) {
        runSearch();
      }
    });

    watch(() => [route.query.title, route.query.author, route.query.limit], () => {
      const previous = form.title;
      syncForm();
      if (form.title && form.title !== previous) {
        runSearch();
      }
      if (!form.title) {
        results.value = [];
        detail.value = null;
        status.value = 'Please enter a book title.';
      }
    });

    return { form, status, results, detail, runSearch, loadDetail };
  }
}, { router: seriesPageRouter });
