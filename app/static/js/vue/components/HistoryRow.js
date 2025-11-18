import { computed, ref, watch } from '../runtime.js';
import { useImport } from '../composables/useImport.js';
import { useVerifyAction, useDeleteAction } from '../composables/useActionButtons.js';
import { useVerificationBadge } from '../composables/useLibraryCheck.js';

export const HistoryRow = {
  name: 'HistoryRow',
  props: {
    item: { type: Object, required: true },
    columnCount: { type: Number, default: 10 }
  },
  emits: ['updated'],
  setup(props, { emit }) {
    const showForm = ref(false);

    // Use composables for import, verify, and delete actions
    const importComposable = useImport(props.item);
    const verifyAction = useVerifyAction(computed(() => props.item));
    const deleteAction = useDeleteAction(computed(() => props.item));
    const { badgeConfig: verifyBadgeConfig } = useVerificationBadge(computed(() => props.item));

    // Watch for form visibility to load data
    watch(showForm, (val) => {
      if (val) importComposable.loadFormData();
    });

    const toggleForm = () => {
      showForm.value = !showForm.value;
    };

    const handleImport = async () => {
      const result = await importComposable.performImport();
      if (result.success) {
        showForm.value = false;
        emit('updated');
      }
    };

    const handleVerify = async () => {
      const result = await verifyAction.performVerify();
      if (result.success) {
        emit('updated');
      }
    };

    const handleRemove = async () => {
      if (!confirm('Remove this history item?')) return;
      const result = await deleteAction.performDelete();
      if (result.success) {
        emit('updated');
      }
    };

    const loadTree = async () => {
      if (!importComposable.form.selectedHash) return;
      importComposable.showTree.value = !importComposable.showTree.value;
      if (importComposable.showTree.value) {
        await importComposable.loadTorrentTree(importComposable.form.selectedHash);
      }
    };

    // Computed properties
    const formattedWhen = computed(() => {
      if (!props.item.added_at) return '';
      return new Date(props.item.added_at.replace(' ', 'T') + 'Z').toLocaleString();
    });

    const statusVariant = computed(() => {
      const map = {
        grey: 'muted',
        blue: 'info',
        yellow: 'warning',
        green: 'success',
        red: 'danger'
      };
      return map[props.item.qb_status_color || 'grey'] || 'muted';
    });

    const statusTooltip = computed(() => props.item.path_warning || '');

    const verifyBadge = computed(() => {
      if (!props.item.imported_at || !verifyBadgeConfig.value) return null;
      const config = verifyBadgeConfig.value;
      const labelMap = {
        'verified': 'Verified',
        'mismatch': 'Mismatch',
        'not_found': 'Missing',
        'unreachable': 'Unreachable',
        'not_configured': 'Not configured'
      };
      return {
        label: labelMap[config.variant] || config.variant,
        variant: config.variant === 'success' ? 'success' :
                 config.variant === 'warning' ? 'warning' :
                 config.variant === 'error' ? 'danger' : 'muted',
        title: config.title
      };
    });

    const detailUrl = computed(() =>
      props.item.mam_id ? `https://www.myanonamouse.net/t/${encodeURIComponent(props.item.mam_id)}` : ''
    );

    const toggleTreeLabel = computed(() =>
      importComposable.showTree.value ? 'Hide Files' : '📁 View Files'
    );

    const treeContents = computed(() => {
      if (!importComposable.torrentTree.value?.files) return [];
      return importComposable.torrentTree.value.files;
    });

    return {
      showForm,
      toggleForm,
      performImport: handleImport,
      verifyItem: handleVerify,
      removeItem: handleRemove,
      formattedWhen,
      statusVariant,
      statusTooltip,
      verifyBadge,
      detailUrl,
      buttonLabel: importComposable.buttonLabel,
      form: importComposable.form,
      torrents: importComposable.torrents,
      statusMessage: importComposable.statusMessage,
      loading: importComposable.loading,
      verifyLoading: verifyAction.verifying,
      removeLoading: deleteAction.deleting,
      loadTree,
      toggleTreeLabel,
      showTree: importComposable.showTree,
      treeContents,
      formLoaded: importComposable.formLoaded
    };
  },
  template: `
      <tr>
        <td style="padding:0.25rem;">
          <img v-if="item.abs_cover_url" :src="item.abs_cover_url" alt="Cover" loading="lazy" style="max-width:60px;max-height:90px;" />
          <span v-else class="muted" style="font-size:0.8em;">No cover</span>
        </td>
        <td>{{ item.title }}</td>
        <td>{{ item.author }}</td>
        <td>{{ item.narrator }}</td>
        <td class="center">
          <a v-if="detailUrl" :href="detailUrl" target="_blank" rel="noopener">🔗</a>
        </td>
        <td>{{ formattedWhen }}</td>
        <td>
          <StatusBadge :label="item.qb_status" :variant="statusVariant" :title="statusTooltip" />
          <StatusBadge v-if="verifyBadge" :label="verifyBadge.label" :variant="verifyBadge.variant" :title="verifyBadge.title" />
        </td>
        <td>
          <ActionButton label="Import" variant="primary" :loading="loading && showForm" @click="toggleForm" />
        </td>
        <td>
          <ActionButton label="Verify" variant="secondary" :loading="verifyLoading" :disabled="!item.imported_at" @click="verifyItem" />
        </td>
        <td>
          <ActionButton label="Remove" variant="danger" :loading="removeLoading" @click="removeItem" />
        </td>
      </tr>
      <tr v-if="showForm">
        <td :colspan="columnCount">
          <div class="import-form">
            <div class="import-form__inputs">
              <label>
                Author
                <input v-model="form.author" type="text" />
              </label>
              <label>
                Title
                <input v-model="form.title" type="text" />
              </label>
              <label>
                Torrent
                <select v-model="form.selectedHash">
                  <option value="" disabled>Select torrent…</option>
                  <option v-for="torrent in torrents" :key="torrent.hash" :value="torrent.hash">
                    {{ torrent.name }}
                  </option>
                </select>
              </label>
              <label class="import-form__inline">
                <input type="checkbox" v-model="form.flatten" /> Flatten multi-disc
              </label>
              <ActionButton :label="buttonLabel" variant="success" :loading="loading" @click="performImport" />
              <ActionButton :label="toggleTreeLabel" variant="secondary" :disabled="!form.selectedHash" @click="loadTree" />
            </div>
            <div class="import-form__status" v-if="statusMessage">{{ statusMessage }}</div>
            <div class="import-form__tree" v-if="showTree">
              <ul>
                <li v-for="file in treeContents" :key="file.path">{{ file.path }} ({{ file.type }})</li>
              </ul>
            </div>
          </div>
        </td>
      </tr>
  `
};
