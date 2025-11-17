import { onMounted, reactive, ref, watch } from '../js/vue/runtime.js';
import { mountVueApp } from '../js/vue/boot.js';
import { useApi } from '../js/vue/composables/useApi.js';
import { useUrlRouter } from '../js/vue/composables/useUrlRouter.js';
import { ShowcaseCard } from '../js/vue/components/ShowcaseCard.js';

mountVueApp('#showcaseApp', {
  components: { ShowcaseCard },
  setup() {
    const api = useApi();
    const router = useUrlRouter({ q: '', limit: '100' });
    const form = reactive({ q: '', limit: '100' });
    const status = ref('Enter a search query to find audiobooks.');
    const groups = ref([]);
    const detailGroup = ref(null);

    const syncForm = () => {
      form.q = router.state.q || '';
      form.limit = router.state.limit || '100';
    };

    const runSearch = async () => {
      if (!form.q.trim()) {
        status.value = 'Enter a search query to find audiobooks.';
        groups.value = [];
        detailGroup.value = null;
        return;
      }
      status.value = 'Loading audiobooks…';
      groups.value = [];
      detailGroup.value = null;
      try {
        const data = await api.getShowcase({ query: form.q.trim(), limit: parseInt(form.limit, 10) });
        groups.value = data.groups || [];
        status.value = groups.value.length ? `Showing ${data.total_groups} titles (${data.total_results} versions)` : 'No audiobooks found.';
        router.updateUrl({ q: form.q.trim(), limit: form.limit }, true);
      } catch (err) {
        status.value = `Failed to load showcase: ${err.message}`;
      }
    };

    const showDetail = (group) => {
      detailGroup.value = group;
    };

    const closeDetail = () => {
      detailGroup.value = null;
    };

    const copyVersion = async (version) => {
      const text = `${version.release_name} — ${version.format} — ${version.length}`;
      try {
        await navigator.clipboard?.writeText(text);
        status.value = 'Copied release info to clipboard';
      } catch {
        status.value = text;
      }
    };

    onMounted(() => {
      syncForm();
      if (form.q) {
        runSearch();
      }
    });

    watch(() => [router.state.q, router.state.limit], () => {
      const previous = form.q;
      syncForm();
      if (form.q && form.q !== previous) {
        runSearch();
      }
      if (!form.q) {
        groups.value = [];
        detailGroup.value = null;
        status.value = 'Enter a search query to find audiobooks.';
      }
    });

    return { form, status, groups, detailGroup, runSearch, showDetail, closeDetail, copyVersion };
  }
});
