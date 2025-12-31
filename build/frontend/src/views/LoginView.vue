<template>
  <div class="login-view">
    <div class="login-container glass-panel">
      <!-- Logo/Brand Header -->
      <div class="login-header">
        <div class="login-logo-wrapper">
          <img :src="logoUrl" alt="Shelfarr logo" class="login-logo" />
        </div>
        <h1 class="login-title">Shelfarr</h1>
        <p class="login-subtitle">Sign in with your Audiobookshelf account</p>
      </div>

      <!-- ABS Not Configured Warning -->
      <n-alert
        v-if="showNotConfigured"
        type="warning"
        title="Audiobookshelf Not Configured"
        class="mb-4"
      >
        <p class="mb-2">
          <code>ABS_BASE_URL</code> is not set in your environment configuration.
          Please configure Audiobookshelf in your <code>.env</code> file and restart the container.
        </p>
        <n-button
          type="primary"
          size="small"
          @click="handleSkipAuth"
        >
          Continue Without Authentication
        </n-button>
      </n-alert>

      <!-- Login Form -->
      <n-form
        v-else-if="authChecked"
        ref="formRef"
        :model="formData"
        :rules="rules"
        label-placement="top"
        @submit.prevent="handleLogin"
      >
        <!-- Username -->
        <n-form-item label="Username" path="username">
          <n-input
            v-model:value="formData.username"
            placeholder="Enter your username"
            :disabled="loading"
            size="large"
            @keyup.enter="handleLogin"
          >
            <template #prefix>
              <span class="input-icon">👤</span>
            </template>
          </n-input>
        </n-form-item>

        <!-- Password -->
        <n-form-item label="Password" path="password">
          <n-input
            v-model:value="formData.password"
            type="password"
            placeholder="Enter your password"
            show-password-on="click"
            :disabled="loading"
            size="large"
            @keyup.enter="handleLogin"
          >
            <template #prefix>
              <span class="input-icon">🔒</span>
            </template>
          </n-input>
        </n-form-item>

        <!-- Error Message -->
        <n-alert
          v-if="error"
          type="error"
          closable
          class="mb-4"
          @close="error = null"
        >
          {{ error }}
        </n-alert>

        <!-- Submit Button -->
        <n-button
          type="primary"
          block
          size="large"
          :loading="loading"
          :disabled="loading"
          @click="handleLogin"
        >
          <template #icon v-if="!loading">
            <span>🔓</span>
          </template>
          Sign In
        </n-button>
      </n-form>

      <!-- Loading State -->
      <div v-else class="loading-state">
        <n-spin size="large" />
        <p class="mt-4 text-gray-400">Checking authentication...</p>
      </div>

      <!-- Footer -->
      <div class="login-footer">
        <p>
          Credentials are validated against your Audiobookshelf server.
          <br />
          No passwords are stored locally.
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NForm, NFormItem, NInput, NButton, NAlert, NSpin } from 'naive-ui'
import { useAuth } from '@composables/useAuth'

const router = useRouter()
const logoUrl = '/static/icon.png'
const {
  absConfigured,
  authStatus,
  loading,
  error,
  checkAuthStatus,
  login,
  skipAuth,
  isAuthenticated
} = useAuth()

const formRef = ref(null)

// Computed
const authChecked = computed(() => authStatus.value.checked)
const showNotConfigured = computed(() => {
  return authChecked.value && !absConfigured.value
})

// Form data
const formData = reactive({
  username: '',
  password: ''
})

// Validation rules
const rules = {
  username: [
    { required: true, message: 'Please enter your username', trigger: 'blur' }
  ],
  password: [
    { required: true, message: 'Please enter your password', trigger: 'blur' }
  ]
}

/**
 * Handle login form submission
 */
const handleLogin = async () => {
  // Validate form
  try {
    await formRef.value?.validate()
  } catch (e) {
    return // Validation failed
  }

  const success = await login(formData.username, formData.password)

  if (success) {
    // Redirect to intended destination or home
    const redirect = router.currentRoute.value.query.redirect || '/'
    router.push(redirect)
  }
}

/**
 * Skip authentication when ABS not configured
 */
const handleSkipAuth = () => {
  skipAuth()
  router.push('/')
}

// Initialize on mount
onMounted(async () => {
  await checkAuthStatus()

  // If already authenticated, redirect home
  if (isAuthenticated.value) {
    const redirect = router.currentRoute.value.query.redirect || '/'
    router.push(redirect)
  }
})
</script>

<style scoped>
.login-view {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-lg);
}

.login-container {
  width: 100%;
  max-width: 420px;
  padding: var(--spacing-xl);
}

.login-header {
  text-align: center;
  margin-bottom: var(--spacing-xl);
}

.login-logo-wrapper {
  width: 192px;
  height: 192px;
  margin: 0 auto var(--spacing-md);
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-logo {
  width: 100%;
  height: 100%;
  object-fit: contain;
  filter:
    drop-shadow(0 14px 40px rgba(0, 0, 0, 0.35))
    drop-shadow(0 10px 30px rgba(80, 0, 0, 0.25));
}

.login-title {
  font-size: 1.75rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: var(--spacing-xs);
}

.login-subtitle {
  color: var(--text-subtle);
  font-size: 0.95rem;
}

.input-icon {
  font-size: 1rem;
  margin-right: 4px;
}

.login-footer {
  margin-top: var(--spacing-xl);
  text-align: center;
  padding-top: var(--spacing-lg);
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.login-footer p {
  font-size: 0.8rem;
  color: var(--text-subtle);
  line-height: 1.5;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--spacing-xl);
}

/* Override Naive UI form item spacing */
:deep(.n-form-item) {
  margin-bottom: var(--spacing-lg);
}

:deep(.n-form-item-label) {
  color: var(--text-secondary);
  font-weight: 500;
}

/* Mobile adjustments */
@media (max-width: 480px) {
  .login-view {
    padding: var(--spacing-md);
    align-items: flex-start;
    padding-top: 10vh;
  }

  .login-container {
    padding: var(--spacing-lg);
  }

  .login-logo-wrapper {
    width: 144px;
    height: 144px;
  }

  .login-title {
    font-size: 1.5rem;
  }
}
</style>
