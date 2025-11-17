import { onMounted, reactive, ref, watch } from '../js/vue/runtime.js';
import { mountVueApp } from '../js/vue/boot.js';
import { useApi } from '../js/vue/composables/useApi.js';
import { useUrlRouter } from '../js/vue/composables/useUrlRouter.js';
import { SeriesTable } from '../js/vue/components/SeriesTable.js';

mountVueApp('#seriesApp', {
  components: { SeriesTable },
  setup() {
    const api = useApi();
    const router = useUrlRouter({ title: '', author: '', limit: '20' });
    const form = reactive({ title: '', author: '', limit: '20' });
    const status = ref('Search for a title to see matching series.');
    const results = ref([]);
    const detail = ref(null);

    const syncForm = () => {
      form.title = router.state.title || '';
      form.author = router.state.author || '';
      form.limit = router.state.limit || '20';
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
        router.updateUrl({ title: form.title.trim(), author: form.author.trim(), limit: form.limit }, true);
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

    watch(() => [router.state.title, router.state.author, router.state.limit], () => {
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
});
