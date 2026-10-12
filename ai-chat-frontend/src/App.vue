<template>
  <div v-if="!token" class="auth-container" :class="theme">
    <div class="auth-bg-circle circle-1"></div>
    <div class="auth-bg-circle circle-2"></div>
    <div class="auth-bg-circle circle-3"></div>
    <div class="auth-box">
      <div class="auth-logo">
        <img v-if="logoUrl" :src="logoUrl" style="width: 80px; height: 80px; border-radius: 20px; object-fit: cover;" />
        <span v-else>🤖</span>
      </div>
      <h2>{{ isRegister ? '创建新账号' : '欢迎回来' }}</h2>
      <p class="auth-subtitle">{{ isRegister ? '开始你的 AI 之旅' : '登录以继续对话' }}</p>
      <div class="input-group"><input v-model="authForm.username" placeholder="用户名" /></div>
      <div class="input-group"><input v-model="authForm.password" type="password" placeholder="密码" @keyup.enter="handleAuth" /></div>
      <button class="auth-btn" @click="handleAuth">{{ isRegister ? '注册' : '登录' }}</button>
      <p class="switch-tip" @click="isRegister = !isRegister">{{ isRegister ? '已有账号？立即登录' : '没有账号？免费注册' }}</p>
      <p v-if="authError" class="error-tip">{{ authError }}</p>
    </div>
  </div>

  <div v-else class="app-layout" :class="theme">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-icon-wrap" @click="triggerLogoUpload" title="点击上传自定义 Logo">
          <img v-if="logoUrl" :src="logoUrl" class="brand-logo" />
          <span v-else class="brand-icon">🤖</span>
          <div class="logo-overlay">📷</div>
        </div>
        <span class="brand-text">AI Chat</span>
        <input ref="logoInputRef" type="file"
               accept="image/png,image/jpeg,image/webp,image/gif,image/svg+xml,image/avif,image/bmp,image/x-icon,image/tiff,image/heic,image/heif,.png,.jpg,.jpeg,.webp,.gif,.svg,.avif,.bmp,.ico,.tif,.tiff,.heic,.heif"
               style="display:none" @change="handleLogoUpload" />
      </div>

      <button class="new-btn" @click="createNewSession"><span class="plus">+</span> 新建对话</button>
      <div class="session-list">
        <div v-for="s in sessions" :key="s.session_id" :class="['session-item', { active: s.session_id === currentSessionId }]" @click="switchSession(s.session_id)">
          <div class="session-icon">💬</div>
          <div class="session-content">
            <div v-if="editingSessionId !== s.session_id" class="preview">{{ s.preview || '新会话' }}</div>
            <input v-else class="rename-input" v-model="editingTitle" @keyup.enter="confirmRename(s.session_id)" @blur="cancelRename" @click.stop autofocus />
            <div class="session-time">{{ formatTime(s.last_time) }}</div>
          </div>
          <div class="session-actions" @click.stop>
            <button class="mini-btn" @click.stop="startRename(s)">✏️</button>
            <button class="mini-btn" @click.stop="confirmDelete(s.session_id)">🗑️</button>
          </div>
        </div>
        <div v-if="sessions.length === 0" class="empty-sessions">暂无历史对话</div>
      </div>
      <div class="user-footer">
        <div class="avatar" @click="triggerLogoUpload" :title="logoUrl ? '点击更换 Logo' : '点击上传头像'">
          <img v-if="logoUrl" :src="logoUrl" style="width:100%;height:100%;object-fit:cover;border-radius:50%;" />
          <span v-else>{{ username.charAt(0).toUpperCase() }}</span>
        </div>
        <div class="user-detail"><div class="user-name">{{ username }}</div><div class="user-status">在线</div></div>
        <button class="theme-btn" @click="toggleTheme">{{ theme === 'dark' ? '🌙' : '☀️' }}</button>
        <button class="logout-btn" @click="logout">⏻</button>
      </div>
    </aside>

    <main class="chat-container">
      <header class="chat-header">
        <div class="header-title"><span class="dot"></span> 与 AI 的对话</div>
        <div class="header-actions">
          <button class="plugin-btn" @click="openPluginModal">🧩 插件</button>
          <button class="plugin-btn" @click="openModelModal">⚙️ 模型</button>
          <button class="export-btn" @click="exportCurrentSession" title="导出对话为 Markdown">📥 导出</button>
          <button class="upload-btn" @click="triggerUpload" :disabled="uploading">{{ uploading ? '⏳' : '📎 上传' }}</button>
          <input ref="fileInputRef" type="file" accept=".pdf,.txt,.md,.docx,.png,.jpg,.jpeg,.webp" style="display:none" @change="handleFileUpload" />
          <div class="header-tag">{{ activeModelLabel }}</div>
        </div>
      </header>

      <div v-if="documents.length > 0" class="doc-bar">
        <span class="doc-bar-label">📚 已选：</span>
        <div v-for="doc in documents" :key="doc.id" :class="['doc-chip', { selected: selectedDocIds.includes(doc.id), processing: doc.status !== 'done' }]" @click="handleDocClick(doc)">
          <span>{{ getDocIcon(doc) }} {{ doc.filename }}</span>
          <span class="doc-meta"><template v-if="doc.status === 'pending'">⏳</template><template v-else-if="doc.status === 'processing'">⚙️</template><template v-else-if="doc.status === 'failed'">❌</template><template v-else>({{ doc.chunk_count }})</template></span>
          <span class="doc-del" @click.stop="removeDoc(doc.id)">×</span>
        </div>
      </div>

      <div class="messages" ref="messagesRef">
        <div v-if="messages.length === 0" class="welcome">
          <div class="welcome-icon">
            <img v-if="logoUrl" :src="logoUrl" style="width: 80px; height: 80px; border-radius: 20px; object-fit: cover;" />
            <span v-else>✨</span>
          </div>
          <h3>开始新的对话吧</h3>
          <p>{{ enabledTools.length > 0 ? '插件已启用，可以问我天气、算数、画图' : '我可以记住你告诉我的每一件事' }}</p>
          <div class="suggestions">
            <div class="suggestion" @click="quickSend('现在几点了？')">现在几点？</div>
            <div class="suggestion" @click="quickSend('画一只戴着墨镜的猫，赛博朋克风格')">画一只猫</div>
            <div class="suggestion" @click="quickSend('北京今天天气怎么样？')">北京天气</div>
          </div>
        </div>

        <div v-for="(msg, idx) in messages" :key="idx" :class="['msg-row', msg.role]">
          <div class="msg-avatar">
            <template v-if="msg.role === 'user'">
              <img v-if="logoUrl" :src="logoUrl" style="width:100%;height:100%;object-fit:cover;border-radius:50%;" />
              <span v-else>你</span>
            </template>
            <template v-else>🤖</template>
          </div>
          <div class="msg-wrap">
            <div v-if="msg.toolCalls && msg.toolCalls.length" class="tool-badges">
              <span v-for="(tc, i) in msg.toolCalls" :key="i" class="tool-badge">🛠 {{ tc.name }}</span>
            </div>
            <div v-if="msg.images && msg.images.length" class="msg-images">
              <div v-for="(img, i) in msg.images" :key="i" class="msg-image-wrap">
                <img :src="img.url" :alt="img.prompt" loading="lazy" />
                <div class="img-prompt">🎨 {{ img.prompt }}</div>
              </div>
            </div>
            <div v-if="msg.content" class="msg-bubble" :class="{ 'md-content': msg.role === 'assistant' }" v-html="renderMarkdown(msg.content)"></div>
            <div v-if="msg.role === 'assistant' && !loading" class="msg-actions"><button @click="regenerate(idx)">🔄 重新生成</button></div>
            <div class="msg-time">{{ msg.time }}</div>
          </div>
        </div>
        <div v-if="loading" class="msg-row assistant">
          <div class="msg-avatar">🤖</div>
          <div class="msg-wrap"><div class="msg-bubble typing-bubble"><span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span></div></div>
        </div>
      </div>

      <div class="input-area">
        <div class="input-wrapper">
          <textarea v-model="input" @keydown.enter.exact.prevent="send" placeholder="输入消息... 试试让我'画一只猫'" :disabled="loading" rows="1" ref="textareaRef" @input="autoResize"></textarea>
          <button class="mic-btn" :class="{ recording: isRecording }" @click="toggleRecording" :disabled="loading">{{ isRecording ? '🔴' : '🎤' }}</button>
          <button v-if="!loading" class="send-btn" @click="send" :disabled="!input.trim()">发送</button>
          <button v-else class="send-btn stop" @click="stopGenerating">⏹</button>
        </div>
      </div>
    </main>

    <!-- ============ 插件管理弹窗 ============ -->
    <div v-if="showPluginModal" class="modal-overlay" @click.self="showPluginModal = false">
      <div class="modal-box" style="width: 550px; max-height: 80vh; overflow-y: auto;">
        <h3>🧩 插件管理</h3>
        <p class="modal-desc">内置插件和自定义插件</p>
        <h4 style="color: var(--text-primary); margin-bottom: 10px;">内置插件</h4>
        <div class="plugin-list">
          <label v-for="tool in availableTools" :key="tool.name" class="plugin-item">
            <input type="checkbox" v-model="tool.enabled" />
            <span class="plugin-icon">{{ tool.icon }}</span>
            <div class="plugin-info"><div class="plugin-name">{{ tool.label }}</div><div class="plugin-desc">{{ tool.desc }}</div></div>
          </label>
        </div>
        <h4 style="color: var(--text-primary); margin: 20px 0 10px;">自定义插件</h4>
        <div class="plugin-list">
          <div v-for="p in customPlugins" :key="p.id" class="plugin-item" style="justify-content: space-between;">
            <div style="display: flex; align-items: center; gap: 12px;">
              <span class="plugin-icon">🧩</span>
              <div class="plugin-info"><div class="plugin-name">{{ p.name }}</div><div class="plugin-desc">{{ p.description }}</div></div>
            </div>
            <button @click="deleteCustomPlugin(p.id)" style="background:none; border:none; color:#ff6b6b; cursor:pointer;">🗑️</button>
          </div>
        </div>
        <div style="margin-top: 20px; border-top: 1px solid var(--border-color); padding-top: 20px;">
          <h4 style="color: var(--text-primary); margin-bottom: 10px;">➕ 添加外部插件</h4>
          <input v-model="newPlugin.name" placeholder="插件名称（英文）" class="modal-input" />
          <input v-model="newPlugin.description" placeholder="用途描述" class="modal-input" />
          <input v-model="newPlugin.url" placeholder="接口 URL" class="modal-input" />
          <select v-model="newPlugin.method" class="modal-input"><option value="GET">GET</option><option value="POST">POST</option></select>
          <textarea v-model="newPlugin.paramsText" placeholder='参数 JSON Schema' class="modal-input" rows="3"></textarea>
          <button class="modal-close" style="margin-top: 10px;" @click="saveCustomPlugin">保存插件</button>
        </div>
        <button class="modal-close" style="margin-top: 10px; background: #555;" @click="showPluginModal = false">关闭</button>
      </div>
    </div>

    <!-- ============ 模型设置弹窗 ============ -->
    <div v-if="showModelModal" class="modal-overlay" @click.self="showModelModal = false">
      <div class="modal-box" style="width: 620px; max-height: 85vh; overflow-y: auto;">
        <h3>⚙️ 模型设置</h3>
        <p class="modal-desc">配置不同的 AI 服务商，一键切换，立即生效。</p>

        <h4 style="color: var(--text-primary); margin-bottom: 10px;">我的配置</h4>
        <div class="plugin-list">
          <div v-for="c in llmConfigs" :key="c.id" class="plugin-item" style="justify-content: space-between;">
            <div style="display: flex; align-items: center; gap: 12px; flex: 1;">
              <span class="plugin-icon">{{ c.is_active ? '🟢' : '⚪' }}</span>
              <div class="plugin-info">
                <div class="plugin-name">{{ c.name }} {{ c.is_active ? '（使用中）' : '' }}</div>
                <div class="plugin-desc">{{ c.chat_model }} · {{ c.api_key_masked }}</div>
              </div>
            </div>
            <div style="display: flex; gap: 6px;">
              <button v-if="!c.is_active" @click="activateConfig(c.id)" class="mini-action">启用</button>
              <button @click="editConfig(c)" class="mini-action">编辑</button>
              <button @click="deleteConfig(c.id)" class="mini-action danger">删除</button>
            </div>
          </div>
          <div v-if="llmConfigs.length === 0" style="text-align: center; color: var(--text-muted); padding: 10px;">
            还没配置，使用默认的 .env 配置
          </div>
        </div>

        <div style="margin-top: 20px; border-top: 1px solid var(--border-color); padding-top: 20px;">
          <h4 style="color: var(--text-primary); margin-bottom: 10px;">
            {{ editingConfigId ? '✏️ 编辑配置' : '➕ 添加新配置' }}
          </h4>

          <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px;">
            <button v-for="(preset, key) in PRESETS" :key="key" @click="applyPreset(key)" class="preset-btn">
              {{ preset.name }}
            </button>
          </div>

          <input v-model="configForm.name" placeholder="配置名称（如：Google Gemini）" class="modal-input" />
          <input v-model="configForm.api_key" placeholder="API Key" class="modal-input" />
          <input v-model="configForm.base_url" placeholder="Base URL" class="modal-input" />
          <input v-model="configForm.chat_model" placeholder="对话模型" class="modal-input" />
          <input v-model="configForm.embedding_model" placeholder="向量化模型（RAG用，可留空）" class="modal-input" />
          <input v-model="configForm.vision_model" placeholder="视觉模型（图片理解用，可留空）" class="modal-input" />
          <input v-model="configForm.image_model" placeholder="画图模型（可留空）" class="modal-input" />

          <div style="display: flex; gap: 8px;">
            <button class="modal-close" style="flex: 1;" @click="saveConfig">
              {{ editingConfigId ? '保存修改' : '添加配置' }}
            </button>
            <button v-if="editingConfigId" class="modal-close" style="flex: 1; background: #555;" @click="resetForm">取消编辑</button>
          </div>
        </div>

        <button class="modal-close" style="margin-top: 10px; background: #555;" @click="showModelModal = false">关闭</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, onUnmounted, computed } from 'vue'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import 'highlight.js/styles/atom-one-dark.css'

const md = new MarkdownIt({
  html: false, linkify: true, breaks: true,
  highlight: (str, lang) => {
    if (lang && hljs.getLanguage(lang)) {
      try { return '<pre class="hljs"><code>' + hljs.highlight(str, { language: lang }).value + '</code></pre>' } catch (_) {}
    }
    return '<pre class="hljs"><code>' + md.utils.escapeHtml(str) + '</code></pre>'
  }
})
const renderMarkdown = (c) => c ? md.render(c) : ''

const theme = ref(localStorage.getItem('theme') || 'dark')
const toggleTheme = () => { theme.value = theme.value === 'dark' ? 'light' : 'dark'; localStorage.setItem('theme', theme.value) }

const token = ref(localStorage.getItem('token') || '')
const username = ref(localStorage.getItem('username') || '')
const logoUrl = ref(localStorage.getItem('logo_url') || '')
const isRegister = ref(false)
const authForm = ref({ username: '', password: '' })
const authError = ref('')

const logoInputRef = ref(null)
const input = ref('')
const messages = ref([])
const loading = ref(false)
const messagesRef = ref(null)
const sessions = ref([])
const currentSessionId = ref('')
const textareaRef = ref(null)
const editingSessionId = ref('')
const editingTitle = ref('')

const documents = ref([])
const selectedDocIds = ref([])
const fileInputRef = ref(null)
const uploading = ref(false)

const showPluginModal = ref(false)
const customPlugins = ref([])
const newPlugin = ref({ name: '', description: '', url: '', method: 'GET', paramsText: '{"type":"object","properties":{}}' })

const availableTools = ref([
  { name: 'get_current_time', label: '获取当前时间', desc: '查询当前日期、时间和星期', icon: '🕒', enabled: true },
  { name: 'get_weather', label: '查询实时天气', desc: '支持全国城市天气查询', icon: '🌤️', enabled: true },
  { name: 'calculate', label: '数学计算器', desc: '进行加减乘除等数学计算', icon: '🔢', enabled: true },
  { name: 'generate_image', label: 'AI 画图', desc: '根据文字描述生成图片（免费）', icon: '🎨', enabled: true },
])
const enabledTools = computed(() => availableTools.value.filter(t => t.enabled).map(t => t.name))

// ============ 模型配置相关 ============
const showModelModal = ref(false)
const llmConfigs = ref([])
const editingConfigId = ref(null)
const configForm = ref({ name: '', api_key: '', base_url: '', chat_model: '', embedding_model: '', vision_model: '', image_model: '' })

// 🌟 预置模板：包含 Google Gemini、硅基流动、Groq 等
const PRESETS = {
  zhipu: { name: '智谱GLM', base_url: 'https://open.bigmodel.cn/api/paas/v4/', chat_model: 'glm-4-flash', embedding_model: 'embedding-3', vision_model: 'glm-4v', image_model: 'cogview-3-flash' },
  deepseek: { name: 'DeepSeek', base_url: 'https://api.deepseek.com/v1', chat_model: 'deepseek-chat', embedding_model: '', vision_model: '', image_model: '' },
  openai: { name: 'OpenAI', base_url: 'https://api.openai.com/v1', chat_model: 'gpt-4o-mini', embedding_model: 'text-embedding-3-small', vision_model: 'gpt-4o', image_model: 'dall-e-3' },
  gemini: { name: 'Google Gemini', base_url: 'https://generativelanguage.googleapis.com/v1beta/openai/', chat_model: 'gemini-2.0-flash', embedding_model: 'text-embedding-004', vision_model: 'gemini-2.0-flash', image_model: '' },
  qwen: { name: '通义千问', base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', chat_model: 'qwen-turbo', embedding_model: 'text-embedding-v3', vision_model: 'qwen-vl-plus', image_model: '' },
  moonshot: { name: '月之暗面', base_url: 'https://api.moonshot.cn/v1', chat_model: 'moonshot-v1-8k', embedding_model: '', vision_model: 'moonshot-v1-8k-vision-preview', image_model: '' },
  siliconflow: { name: '硅基流动', base_url: 'https://api.siliconflow.cn/v1', chat_model: 'Qwen/Qwen2.5-7B-Instruct', embedding_model: 'BAAI/bge-m3', vision_model: '', image_model: 'Kwai-Kolors/Kolors' },
  groq: { name: 'Groq', base_url: 'https://api.groq.com/openai/v1', chat_model: 'llama-3.3-70b-versatile', embedding_model: '', vision_model: 'llama-3.2-90b-vision-preview', image_model: '' },
}

const activeModelLabel = computed(() => {
  const active = llmConfigs.value.find(c => c.is_active)
  return active ? active.chat_model : 'GLM-4-Flash'
})

function openModelModal() {
  showModelModal.value = true
  loadLLMConfigs()
}

async function loadLLMConfigs() {
  try {
    const res = await fetch('http://localhost:8000/llm/configs', { headers: getHeaders() })
    if (res.ok) llmConfigs.value = await res.json()
  } catch (e) { console.error(e) }
}

function applyPreset(key) {
  const p = PRESETS[key]
  configForm.value = {
    name: p.name,
    api_key: configForm.value.api_key,
    base_url: p.base_url,
    chat_model: p.chat_model,
    embedding_model: p.embedding_model,
    vision_model: p.vision_model,
    image_model: p.image_model
  }
}

function editConfig(c) {
  editingConfigId.value = c.id
  configForm.value = {
    name: c.name, api_key: '',
    base_url: c.base_url, chat_model: c.chat_model,
    embedding_model: c.embedding_model || '',
    vision_model: c.vision_model || '',
    image_model: c.image_model || ''
  }
  alert('出于安全考虑，API Key 未返回。若无需更换请留空并点击保存，若需更换请重新填入。')
}

function resetForm() {
  editingConfigId.value = null
  configForm.value = { name: '', api_key: '', base_url: '', chat_model: '', embedding_model: '', vision_model: '', image_model: '' }
}

async function saveConfig() {
  if (!configForm.value.name || !configForm.value.base_url || !configForm.value.chat_model) {
    return alert('配置名称、Base URL、对话模型不能为空')
  }
  if (!editingConfigId.value && !configForm.value.api_key) {
    return alert('新增配置时 API Key 不能为空')
  }
  const url = editingConfigId.value
    ? `http://localhost:8000/llm/configs/${editingConfigId.value}`
    : 'http://localhost:8000/llm/configs'
  const method = editingConfigId.value ? 'PUT' : 'POST'
  try {
    const res = await fetch(url, { method, headers: getHeaders(), body: JSON.stringify(configForm.value) })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || '操作失败')
    await loadLLMConfigs()
    resetForm()
    alert('✅ 保存成功')
  } catch (e) { alert('❌ ' + e.message) }
}

async function activateConfig(id) {
  try {
    await fetch(`http://localhost:8000/llm/configs/${id}/activate`, { method: 'POST', headers: getHeaders() })
    await loadLLMConfigs()
  } catch (e) { console.error(e) }
}

async function deleteConfig(id) {
  if (!confirm('确定删除这个配置？')) return
  try {
    await fetch(`http://localhost:8000/llm/configs/${id}`, { method: 'DELETE', headers: getHeaders() })
    await loadLLMConfigs()
  } catch (e) { console.error(e) }
}

// ============ 语音输入 ============
const isRecording = ref(false)
let recognition = null
if (typeof window !== 'undefined' && (window.SpeechRecognition || window.webkitSpeechRecognition)) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
  recognition = new SpeechRecognition()
  recognition.continuous = false; recognition.interimResults = true; recognition.lang = 'zh-CN'
  recognition.onresult = (event) => { let t = ''; for (let i = event.resultIndex; i < event.results.length; i++) t += event.results[i][0].transcript; input.value = t }
  recognition.onend = () => { isRecording.value = false }
  recognition.onerror = () => { isRecording.value = false }
}
const toggleRecording = () => {
  if (!recognition) return alert('当前浏览器不支持语音输入，请使用 Chrome 或 Edge')
  if (isRecording.value) { recognition.stop(); isRecording.value = false } else { recognition.start(); isRecording.value = true }
}

let abortController = null
let pollTimer = null
const getHeaders = () => ({ 'Content-Type': 'application/json', 'Authorization': `Bearer ${token.value}` })
const getNowTime = () => { const d = new Date(); return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}` }
const formatTime = (t) => { if (!t) return ''; const date = new Date(t); const diff = (new Date() - date) / 1000; if (diff < 60) return '刚刚'; if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`; if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`; return `${date.getMonth() + 1}月${date.getDate()}日` }
const getDocIcon = (doc) => { const exts = ['png','jpg','jpeg','webp']; if (exts.includes(doc.file_type)) return '🖼️'; if (doc.file_type === 'pdf') return '📕'; if (doc.file_type === 'docx') return '📘'; return '📄' }

async function handleAuth() {
  authError.value = ''
  const url = isRegister.value ? 'http://localhost:8000/register' : 'http://localhost:8000/login'
  try {
    const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(authForm.value) })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || '操作失败')
    if (isRegister.value) { isRegister.value = false; authError.value = '✅ 注册成功，请登录' }
    else {
      token.value = data.access_token; username.value = data.username
      if (data.logo_url) { logoUrl.value = data.logo_url; localStorage.setItem('logo_url', data.logo_url) }
      localStorage.setItem('token', data.access_token); localStorage.setItem('username', data.username)
      await initChat()
    }
  } catch (e) { authError.value = e.message }
}

function logout() {
  token.value = ''; username.value = ''; logoUrl.value = ''
  localStorage.removeItem('token'); localStorage.removeItem('username'); localStorage.removeItem('logo_url')
  messages.value = []; sessions.value = []; documents.value = []; selectedDocIds.value = []
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

function triggerLogoUpload() { logoInputRef.value?.click() }

async function handleLogoUpload(e) {
  const file = e.target.files[0]; if (!file) return
  const ext = file.name.split('.').pop().toLowerCase()
  const allowed = ['png','jpg','jpeg','webp','gif','svg','avif','bmp','ico','tif','tiff','heic','heif']
  if (!allowed.includes(ext)) {
    alert(`❌ 不支持的格式 .${ext}\n支持：${allowed.join(', ')}`)
    e.target.value = ''
    return
  }
  if (file.size > 5 * 1024 * 1024) {
    alert('❌ 图片超过 5MB 限制')
    e.target.value = ''
    return
  }
  const fd = new FormData(); fd.append('file', file)
  try {
    const res = await fetch('http://localhost:8000/user/logo', {
      method: 'POST', headers: { 'Authorization': `Bearer ${token.value}` }, body: fd
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || '上传失败')
    logoUrl.value = data.logo_url + '?t=' + Date.now()
    localStorage.setItem('logo_url', logoUrl.value)
  } catch (err) { alert('❌ ' + err.message) } finally { e.target.value = '' }
}

async function initChat() {
  await Promise.all([loadSessions(), loadDocuments(), loadCustomPlugins(), loadLLMConfigs()])
  if (sessions.value.length > 0) switchSession(sessions.value[0].session_id)
  else createNewSession()
  startPolling()
}

const createNewSession = () => { currentSessionId.value = `session_${Date.now()}`; messages.value = [] }

async function switchSession(sessionId) {
  if (currentSessionId.value === sessionId || loading.value) return
  currentSessionId.value = sessionId; messages.value = []
  try {
    const res = await fetch(`http://localhost:8000/history/${sessionId}`, { headers: getHeaders() })
    if (res.ok) {
      const history = await res.json()
      messages.value = history.map(m => ({ ...m, time: getNowTime(), toolCalls: [], images: [] }))
      await scrollToBottom()
    }
  } catch (e) {}
}

async function loadSessions() { try { const res = await fetch('http://localhost:8000/sessions', { headers: getHeaders() }); if (res.ok) sessions.value = await res.json() } catch (e) {} }
async function loadDocuments() { try { const res = await fetch('http://localhost:8000/documents', { headers: getHeaders() }); if (res.ok) documents.value = await res.json() } catch (e) {} }
async function loadCustomPlugins() { try { const res = await fetch('http://localhost:8000/plugins', { headers: getHeaders() }); if (res.ok) customPlugins.value = await res.json() } catch (e) {} }

function startPolling() {
  if (pollTimer) return
  pollTimer = setInterval(async () => { if (!token.value) return; const hasPending = documents.value.some(d => d.status !== 'done'); if (hasPending) await loadDocuments() }, 2000)
}

function triggerUpload() { fileInputRef.value?.click() }

async function handleFileUpload(e) {
  const file = e.target.files[0]; if (!file) return
  uploading.value = true; const fd = new FormData(); fd.append('file', file)
  try {
    const res = await fetch('http://localhost:8000/upload', { method: 'POST', headers: { 'Authorization': `Bearer ${token.value}` }, body: fd })
    const data = await res.json(); if (!res.ok) throw new Error(data.detail || '上传失败'); await loadDocuments()
  } catch (e) { alert('❌ ' + e.message) } finally { uploading.value = false; e.target.value = '' }
}

function handleDocClick(doc) { if (doc.status !== 'done') return; toggleDoc(doc.id) }
function toggleDoc(id) { const i = selectedDocIds.value.indexOf(id); if (i >= 0) selectedDocIds.value.splice(i, 1); else selectedDocIds.value.push(id) }
async function removeDoc(id) { if (!confirm('删除这个文档？')) return; try { await fetch(`http://localhost:8000/documents/${id}`, { method: 'DELETE', headers: getHeaders() }); selectedDocIds.value = selectedDocIds.value.filter(x => x !== id); await loadDocuments() } catch (e) {} }

function startRename(s) { editingSessionId.value = s.session_id; editingTitle.value = s.preview || '' }
function cancelRename() { editingSessionId.value = ''; editingTitle.value = '' }
async function confirmRename(sessionId) { const t = editingTitle.value.trim(); if (!t) return cancelRename(); try { await fetch(`http://localhost:8000/sessions/${sessionId}/rename`, { method: 'PUT', headers: getHeaders(), body: JSON.stringify({ new_title: t }) }); await loadSessions() } catch (e) {}; cancelRename() }
async function confirmDelete(sessionId) { if (!confirm('确定删除会话？')) return; try { await fetch(`http://localhost:8000/sessions/${sessionId}`, { method: 'DELETE', headers: getHeaders() }); if (currentSessionId.value === sessionId) { currentSessionId.value = ''; messages.value = [] }; await loadSessions(); if (sessions.value.length > 0) switchSession(sessions.value[0].session_id); else createNewSession() } catch (e) {} }

function openPluginModal() { showPluginModal.value = true }

async function saveCustomPlugin() {
  if (!newPlugin.value.name || !newPlugin.value.url) return alert('插件名称和 URL 不能为空')
  let params = {}
  try { params = JSON.parse(newPlugin.value.paramsText) } catch (e) { return alert('参数 JSON 格式错误') }
  try {
    const res = await fetch('http://localhost:8000/plugins', {
      method: 'POST', headers: getHeaders(),
      body: JSON.stringify({ name: newPlugin.value.name, description: newPlugin.value.description, method: newPlugin.value.method, url: newPlugin.value.url, params_schema: params })
    })
    if (res.ok) { await loadCustomPlugins(); newPlugin.value = { name: '', description: '', url: '', method: 'GET', paramsText: '{"type":"object","properties":{}}' } }
  } catch (e) { alert('添加失败') }
}

async function deleteCustomPlugin(id) { if (!confirm('删除这个插件？')) return; try { await fetch(`http://localhost:8000/plugins/${id}`, { method: 'DELETE', headers: getHeaders() }); await loadCustomPlugins() } catch (e) {} }

function quickSend(text) { input.value = text; send() }
function autoResize() { const el = textareaRef.value; if (el) { el.style.height = 'auto'; el.style.height = Math.min(el.scrollHeight, 150) + 'px' } }

// ============ 导出当前会话为 Markdown ============
function exportCurrentSession() {
  if (!messages.value.length) return alert('当前会话没有消息')
  const title = sessions.value.find(s => s.session_id === currentSessionId.value)?.preview || '对话记录'
  let mdText = `# ${title}\n\n导出时间：${new Date().toLocaleString()}\n\n---\n\n`
  for (const m of messages.value) {
    mdText += `## ${m.role === 'user' ? '👤 你' : '🤖 AI'}\n\n${m.content}\n\n`
    if (m.images && m.images.length) {
      for (const img of m.images) mdText += `![图片](${img.url})\n\n`
    }
  }
  const blob = new Blob([mdText], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `chat_${Date.now()}.md`
  a.click()
  URL.revokeObjectURL(url)
}

async function send() {
  if (!input.value.trim() || loading.value) return
  if (!currentSessionId.value) createNewSession()
  const userMsg = input.value; input.value = ''
  if (textareaRef.value) textareaRef.value.style.height = 'auto'
  const nowTime = getNowTime()
  messages.value.push({ role: 'user', content: userMsg, time: nowTime, toolCalls: [], images: [] })
  messages.value.push({ role: 'assistant', content: '', time: nowTime, toolCalls: [], images: [] })
  loading.value = true; await scrollToBottom()
  abortController = new AbortController()

  const enabledToolNames = enabledTools.value.concat(customPlugins.value.map(p => p.name))

  try {
    const response = await fetch('http://localhost:8000/chat', {
      method: 'POST', headers: getHeaders(), signal: abortController.signal,
      body: JSON.stringify({ session_id: currentSessionId.value, message: userMsg, doc_ids: selectedDocIds.value, use_tools: enabledToolNames.length > 0, enabled_tools: enabledToolNames })
    })
    if (response.status === 401) { logout(); return }
    const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = ''
    const currentMsg = messages.value[messages.value.length - 1]
    while (true) {
      const { done, value } = await reader.read(); if (done) break
      buffer += decoder.decode(value, { stream: true }); const lines = buffer.split('\n\n'); buffer = lines.pop()
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const data = line.slice(6); if (data === '[DONE]') continue
        try {
          const evt = JSON.parse(data)
          if (evt.type === 'content') { currentMsg.content += evt.content; await scrollToBottom() }
          else if (evt.type === 'tool_call') { currentMsg.toolCalls.push({ name: evt.name, args: evt.args }) }
          else if (evt.type === 'image') { if (!currentMsg.images) currentMsg.images = []; currentMsg.images.push({ url: evt.url, prompt: evt.prompt }); await scrollToBottom() }
        } catch (e) {}
      }
    }
  } catch (e) {
    if (e.name === 'AbortError') messages.value[messages.value.length - 1].content += '\n\n*(已停止生成)*'
    else messages.value[messages.value.length - 1].content = '❌ 请求失败：' + e.message
  }
  finally { loading.value = false; abortController = null; await loadSessions() }
}

function stopGenerating() { if (abortController) abortController.abort() }

async function regenerate(idx) {
  if (loading.value) return
  let userIdx = -1; for (let i = idx - 1; i >= 0; i--) { if (messages.value[i].role === 'user') { userIdx = i; break } }
  if (userIdx === -1) return
  const userMsg = messages.value[userIdx].content; messages.value.splice(userIdx, messages.value.length - userIdx)
  input.value = userMsg; await send()
}

async function scrollToBottom() { await nextTick(); if (messagesRef.value) messagesRef.value.scrollTop = messagesRef.value.scrollHeight }

onMounted(() => { if (token.value) initChat() })
onUnmounted(() => { if (pollTimer) clearInterval(pollTimer) })
</script>

<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
.app-layout.dark, .auth-container.dark { --bg-main: #0f0f1a; --bg-sidebar: #15151f; --bg-card: rgba(255,255,255,0.05); --bg-card-hover: rgba(255,255,255,0.08); --border-color: rgba(255,255,255,0.06); --border-color-strong: rgba(255,255,255,0.1); --text-primary: #ffffff; --text-secondary: #c5c5d5; --text-muted: #8888a0; --text-faint: #666680; --input-bg: rgba(255,255,255,0.03); }
.app-layout.light, .auth-container.light { --bg-main: #f7f8fa; --bg-sidebar: #ffffff; --bg-card: rgba(0,0,0,0.03); --bg-card-hover: rgba(0,0,0,0.06); --border-color: rgba(0,0,0,0.06); --border-color-strong: rgba(0,0,0,0.1); --text-primary: #1a1a2e; --text-secondary: #333344; --text-muted: #666680; --text-faint: #999; --input-bg: rgba(0,0,0,0.02); }
.auth-container { position: relative; display: flex; justify-content: center; align-items: center; height: 100vh; background: var(--bg-main); overflow: hidden; font-family: -apple-system, "Microsoft YaHei", sans-serif; }
.auth-bg-circle { position: absolute; border-radius: 50%; filter: blur(80px); opacity: 0.5; animation: float 20s ease-in-out infinite; }
.circle-1 { width: 400px; height: 400px; background: #3b82f6; top: -100px; left: -100px; }
.circle-2 { width: 350px; height: 350px; background: #06b6d4; bottom: -80px; right: -80px; animation-delay: -5s; }
.circle-3 { width: 300px; height: 300px; background: #2563eb; top: 40%; left: 60%; animation-delay: -10s; }
@keyframes float { 0%,100% { transform: translate(0,0) scale(1); } 50% { transform: translate(30px,-30px) scale(1.1); } }
.auth-box { position: relative; z-index: 1; background: var(--bg-card); backdrop-filter: blur(20px); border: 1px solid var(--border-color-strong); padding: 48px 40px; border-radius: 24px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); width: 380px; display: flex; flex-direction: column; gap: 14px; animation: slideUp 0.6s ease; }
@keyframes slideUp { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: translateY(0); } }
.auth-logo { font-size: 56px; text-align: center; margin-bottom: 8px; animation: bounce 2s ease infinite; display: flex; justify-content: center; align-items: center; }
@keyframes bounce { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-8px); } }
.auth-box h2 { color: var(--text-primary); text-align: center; font-size: 24px; font-weight: 600; }
.auth-subtitle { color: var(--text-muted); text-align: center; font-size: 14px; margin-bottom: 16px; }
.input-group input { width: 100%; padding: 14px 18px; background: var(--input-bg); border: 1px solid var(--border-color-strong); border-radius: 12px; font-size: 15px; color: var(--text-primary); outline: none; transition: all 0.2s; }
.input-group input::placeholder { color: var(--text-faint); }
.input-group input:focus { border-color: #3b82f6; background: rgba(59,130,246,0.08); box-shadow: 0 0 0 3px rgba(59,130,246,0.2); }
.auth-btn { padding: 14px; background: linear-gradient(135deg,#3b82f6,#06b6d4); color: white; border: none; border-radius: 12px; font-size: 16px; font-weight: 600; cursor: pointer; margin-top: 8px; transition: all 0.3s; }
.auth-btn:hover { transform: translateY(-2px); box-shadow: 0 10px 25px rgba(59,130,246,0.4); }
.switch-tip { text-align: center; color: var(--text-muted); cursor: pointer; font-size: 13px; }
.switch-tip:hover { color: #93c5fd; }
.error-tip { color: #ff6b6b; font-size: 13px; text-align: center; }
.app-layout { display: flex; height: 100vh; font-family: -apple-system, "Microsoft YaHei", sans-serif; background: var(--bg-main); color: var(--text-primary); }
.sidebar { width: 280px; background: var(--bg-sidebar); border-right: 1px solid var(--border-color); display: flex; flex-direction: column; padding: 20px 16px; }
.brand { display: flex; align-items: center; gap: 10px; padding: 8px 12px; margin-bottom: 20px; }
.brand-icon-wrap { position: relative; width: 36px; height: 36px; border-radius: 10px; cursor: pointer; overflow: hidden; display: flex; align-items: center; justify-content: center; background: rgba(59,130,246,0.1); transition: all 0.2s; }
.brand-icon-wrap:hover { transform: scale(1.05); box-shadow: 0 0 0 2px rgba(59,130,246,0.5); }
.brand-icon { font-size: 22px; }
.brand-logo { width: 100%; height: 100%; object-fit: cover; }
.logo-overlay { position: absolute; inset: 0; background: rgba(0,0,0,0.6); color: white; font-size: 14px; display: flex; align-items: center; justify-content: center; opacity: 0; transition: opacity 0.2s; }
.brand-icon-wrap:hover .logo-overlay { opacity: 1; }
.brand-text { font-size: 18px; font-weight: 700; background: linear-gradient(135deg,#3b82f6,#06b6d4); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.new-btn { display: flex; align-items: center; justify-content: center; gap: 8px; padding: 12px; background: linear-gradient(135deg,#3b82f6,#2563eb); color: white; border: none; border-radius: 12px; cursor: pointer; font-size: 14px; font-weight: 600; margin-bottom: 20px; transition: all 0.2s; }
.new-btn:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(59,130,246,0.35); }
.plus { font-size: 18px; }
.session-list { flex: 1; overflow-y: auto; margin-bottom: 16px; }
.session-item { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 10px; cursor: pointer; margin-bottom: 4px; transition: all 0.2s; position: relative; }
.session-item:hover { background: var(--bg-card-hover); }
.session-item.active { background: linear-gradient(135deg, rgba(59,130,246,0.2), rgba(6,182,212,0.1)); border: 1px solid rgba(59,130,246,0.3); }
.session-icon { font-size: 16px; }
.session-content { flex: 1; overflow: hidden; }
.preview { font-size: 13px; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-weight: 500; }
.session-time { font-size: 11px; color: var(--text-faint); margin-top: 2px; }
.rename-input { width: 100%; padding: 4px 8px; background: var(--input-bg); border: 1px solid #3b82f6; border-radius: 6px; color: var(--text-primary); font-size: 13px; outline: none; }
.session-actions { display: none; gap: 2px; }
.session-item:hover .session-actions { display: flex; }
.mini-btn { background: none; border: none; cursor: pointer; font-size: 12px; padding: 4px; border-radius: 4px; opacity: 0.6; }
.mini-btn:hover { opacity: 1; background: var(--bg-card-hover); }
.empty-sessions { text-align: center; color: var(--text-faint); font-size: 13px; padding: 20px; }
.user-footer { display: flex; align-items: center; gap: 8px; padding: 10px 12px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border-color); }
.avatar { width: 34px; height: 34px; background: linear-gradient(135deg,#3b82f6,#06b6d4); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 14px; color: white; flex-shrink: 0; cursor: pointer; overflow: hidden; transition: all 0.2s; }
.avatar:hover { transform: scale(1.05); box-shadow: 0 0 0 2px rgba(59,130,246,0.5); }
.user-detail { flex: 1; overflow: hidden; }
.user-name { font-size: 13px; font-weight: 600; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.user-status { font-size: 11px; color: #22c55e; }
.theme-btn, .logout-btn { background: none; border: none; color: var(--text-faint); font-size: 16px; cursor: pointer; padding: 4px 6px; border-radius: 6px; transition: all 0.2s; }
.theme-btn:hover { color: #fbbf24; }
.logout-btn:hover { color: #ff6b6b; }
.chat-container { flex: 1; display: flex; flex-direction: column; background: var(--bg-main); position: relative; }
.chat-header { display: flex; justify-content: space-between; align-items: center; padding: 12px 20px; border-bottom: 1px solid var(--border-color); background: var(--bg-sidebar); gap: 12px; }
.header-title { display: flex; align-items: center; gap: 10px; font-size: 15px; font-weight: 600; }
.header-actions { display: flex; align-items: center; gap: 10px; }
.dot { width: 8px; height: 8px; background: #22c55e; border-radius: 50%; box-shadow: 0 0 8px #22c55e; animation: pulse 2s infinite; }
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.5; } }
.header-tag { font-size: 12px; color: var(--text-muted); background: rgba(59,130,246,0.15); padding: 4px 12px; border-radius: 20px; border: 1px solid rgba(59,130,246,0.3); }
.plugin-btn { padding: 6px 14px; background: rgba(139,92,246,0.15); color: #a78bfa; border: 1px solid rgba(139,92,246,0.3); border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 500; transition: all 0.2s; }
.plugin-btn:hover { background: rgba(139,92,246,0.25); }
.export-btn { padding: 6px 14px; background: rgba(34,197,94,0.15); color: #4ade80; border: 1px solid rgba(34,197,94,0.3); border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 500; transition: all 0.2s; }
.export-btn:hover { background: rgba(34,197,94,0.25); }
.upload-btn { padding: 6px 14px; background: linear-gradient(135deg,#3b82f6,#2563eb); color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 500; transition: all 0.2s; }
.upload-btn:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(59,130,246,0.35); }
.upload-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.doc-bar { padding: 10px 20px; background: var(--bg-card); border-bottom: 1px solid var(--border-color); display: flex; gap: 8px; flex-wrap: wrap; align-items: center; font-size: 12px; }
.doc-bar-label { color: var(--text-muted); }
.doc-chip { display: flex; align-items: center; gap: 6px; padding: 4px 10px; background: var(--bg-sidebar); border: 1px solid var(--border-color-strong); border-radius: 16px; cursor: pointer; transition: all 0.2s; color: var(--text-secondary); font-size: 12px; }
.doc-chip:hover { border-color: #3b82f6; }
.doc-chip.selected { background: rgba(59,130,246,0.2); border-color: #3b82f6; color: var(--text-primary); }
.doc-chip.processing { opacity: 0.7; cursor: not-allowed; }
.doc-icon { font-size: 14px; }
.doc-meta { color: var(--text-faint); font-size: 11px; }
.doc-del { color: var(--text-faint); font-size: 14px; padding: 0 2px; }
.doc-del:hover { color: #ff6b6b; }
.messages { flex: 1; overflow-y: auto; padding: 30px 40px; }
.welcome { text-align: center; padding: 60px 20px; }
.welcome-icon { font-size: 56px; margin-bottom: 16px; animation: bounce 2s ease infinite; display: flex; justify-content: center; }
.welcome h3 { font-size: 24px; color: var(--text-primary); margin-bottom: 8px; }
.welcome p { color: var(--text-muted); font-size: 14px; margin-bottom: 30px; }
.suggestions { display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; }
.suggestion { padding: 12px 20px; background: var(--bg-card); border: 1px solid var(--border-color-strong); border-radius: 12px; color: var(--text-secondary); font-size: 13px; cursor: pointer; transition: all 0.2s; }
.suggestion:hover { background: rgba(59,130,246,0.1); border-color: rgba(59,130,246,0.4); color: var(--text-primary); transform: translateY(-2px); }
.msg-row { display: flex; gap: 12px; margin-bottom: 24px; animation: fadeIn 0.3s ease; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
.msg-row.user { flex-direction: row-reverse; }
.msg-avatar { width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 700; flex-shrink: 0; overflow: hidden; }
.msg-row.user .msg-avatar { background: linear-gradient(135deg,#3b82f6,#2563eb); color: white; }
.msg-row.assistant .msg-avatar { background: rgba(6,182,212,0.15); border: 1px solid rgba(6,182,212,0.3); }
.msg-wrap { max-width: 72%; display: flex; flex-direction: column; }
.msg-row.user .msg-wrap { align-items: flex-end; }
.msg-bubble { padding: 12px 18px; border-radius: 16px; font-size: 15px; line-height: 1.7; word-wrap: break-word; white-space: pre-wrap; }
.msg-row.user .msg-bubble { background: linear-gradient(135deg,#3b82f6,#2563eb); color: white; border-top-right-radius: 4px; }
.msg-row.assistant .msg-bubble { background: var(--bg-card); border: 1px solid var(--border-color-strong); color: var(--text-primary); border-top-left-radius: 4px; }
.msg-time { font-size: 11px; color: var(--text-faint); margin-top: 4px; padding: 0 4px; }
.tool-badges { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 6px; }
.tool-badge { font-size: 11px; color: #22c55e; background: rgba(34,197,94,0.1); border: 1px solid rgba(34,197,94,0.3); padding: 3px 10px; border-radius: 12px; }
.msg-images { display: flex; flex-direction: column; gap: 10px; margin-bottom: 10px; }
.msg-image-wrap { border-radius: 14px; overflow: hidden; border: 1px solid var(--border-color-strong); background: var(--bg-card); animation: fadeIn 0.4s ease; }
.msg-image-wrap img { display: block; width: 100%; max-width: 400px; height: auto; cursor: zoom-in; transition: transform 0.3s; }
.msg-image-wrap img:hover { transform: scale(1.02); }
.img-prompt { padding: 8px 14px; font-size: 12px; color: var(--text-muted); border-top: 1px solid var(--border-color); background: var(--bg-sidebar); }
.msg-actions { display: none; margin-top: 6px; }
.msg-row.assistant:hover .msg-actions { display: block; }
.msg-actions button { background: none; border: 1px solid var(--border-color-strong); color: var(--text-muted); font-size: 12px; padding: 4px 10px; border-radius: 8px; cursor: pointer; transition: all 0.2s; }
.msg-actions button:hover { color: #3b82f6; border-color: #3b82f6; }
.md-content :deep(p) { margin: 6px 0; }
.md-content :deep(h1),.md-content :deep(h2),.md-content :deep(h3),.md-content :deep(h4) { margin: 12px 0 6px 0; color: var(--text-primary); }
.md-content :deep(ul),.md-content :deep(ol) { margin: 6px 0; padding-left: 24px; }
.md-content :deep(li) { margin: 3px 0; }
.md-content :deep(code) { background: rgba(59,130,246,0.15); padding: 2px 6px; border-radius: 4px; font-size: 13px; font-family: 'Consolas','Monaco',monospace; }
.md-content :deep(pre.hljs) { background: #1e1e2e !important; border-radius: 10px; padding: 16px; margin: 10px 0; overflow-x: auto; border: 1px solid rgba(255,255,255,0.08); }
.md-content :deep(pre.hljs code) { background: none !important; padding: 0; color: #e5e5f0; font-size: 13px; line-height: 1.6; font-family: 'Consolas','Monaco',monospace; }
.md-content :deep(blockquote) { border-left: 3px solid #3b82f6; padding: 4px 12px; margin: 8px 0; color: var(--text-muted); background: rgba(59,130,246,0.05); border-radius: 0 6px 6px 0; }
.md-content :deep(table) { border-collapse: collapse; margin: 10px 0; font-size: 14px; }
.md-content :deep(th),.md-content :deep(td) { border: 1px solid var(--border-color-strong); padding: 8px 12px; text-align: left; }
.md-content :deep(th) { background: var(--bg-card-hover); font-weight: 600; }
.md-content :deep(a) { color: #3b82f6; text-decoration: none; }
.typing-bubble { display: flex; gap: 4px; padding: 14px 18px; }
.typing-dot { width: 6px; height: 6px; background: #3b82f6; border-radius: 50%; animation: typingBounce 1.4s infinite; }
.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes typingBounce { 0%,60%,100% { transform: translateY(0); opacity: 0.4; } 30% { transform: translateY(-8px); opacity: 1; } }
.input-area { padding: 20px 40px 30px; }
.input-wrapper { display: flex; gap: 10px; align-items: flex-end; background: var(--bg-card); border: 1px solid var(--border-color-strong); border-radius: 16px; padding: 8px 8px 8px 20px; transition: all 0.2s; }
.input-wrapper:focus-within { border-color: rgba(59,130,246,0.5); box-shadow: 0 0 0 3px rgba(59,130,246,0.15); }
.input-wrapper textarea { flex: 1; background: none; border: none; color: var(--text-primary); font-size: 15px; outline: none; resize: none; padding: 10px 0; font-family: inherit; line-height: 1.5; max-height: 150px; }
.input-wrapper textarea::placeholder { color: var(--text-faint); }
.mic-btn { background: none; border: 1px solid var(--border-color-strong); font-size: 18px; padding: 8px 12px; border-radius: 12px; cursor: pointer; transition: all 0.2s; color: var(--text-secondary); }
.mic-btn:hover { border-color: #3b82f6; color: #3b82f6; }
.mic-btn.recording { background: rgba(239,68,68,0.15); border-color: #ef4444; color: #ef4444; animation: pulse 1.5s infinite; }
.send-btn { padding: 10px 24px; background: linear-gradient(135deg,#3b82f6,#06b6d4); color: white; border: none; border-radius: 12px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.2s; flex-shrink: 0; }
.send-btn:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(59,130,246,0.35); }
.send-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.send-btn.stop { background: linear-gradient(135deg, #ef4444, #f97316); }
.modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.6); backdrop-filter: blur(4px); display: flex; justify-content: center; align-items: center; z-index: 1000; }
.modal-box { background: var(--bg-sidebar); border: 1px solid var(--border-color-strong); border-radius: 20px; padding: 28px; width: 400px; box-shadow: 0 20px 60px rgba(0,0,0,0.5); }
.modal-box h3 { color: var(--text-primary); margin-bottom: 8px; font-size: 18px; }
.modal-desc { color: var(--text-muted); font-size: 13px; margin-bottom: 20px; }
.plugin-list { display: flex; flex-direction: column; gap: 12px; margin-bottom: 24px; }
.plugin-item { display: flex; align-items: center; gap: 12px; padding: 10px 14px; background: var(--bg-card); border-radius: 12px; cursor: pointer; transition: all 0.2s; }
.plugin-item:hover { background: var(--bg-card-hover); }
.plugin-item input { width: 18px; height: 18px; accent-color: #3b82f6; cursor: pointer; }
.plugin-icon { font-size: 20px; }
.plugin-info { flex: 1; }
.plugin-name { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.plugin-desc { font-size: 12px; color: var(--text-muted); }
.modal-close { width: 100%; padding: 12px; background: linear-gradient(135deg,#3b82f6,#06b6d4); color: white; border: none; border-radius: 12px; font-size: 15px; font-weight: 600; cursor: pointer; }
.modal-close:hover { opacity: 0.9; }
.modal-input { width: 100%; padding: 10px 14px; background: var(--bg-card); border: 1px solid var(--border-color-strong); border-radius: 10px; color: var(--text-primary); font-size: 13px; margin-bottom: 10px; outline: none; font-family: inherit; }
.modal-input:focus { border-color: #3b82f6; }
.mini-action { padding: 4px 10px; font-size: 12px; border: 1px solid var(--border-color-strong); background: transparent; color: var(--text-secondary); border-radius: 6px; cursor: pointer; transition: all 0.2s; }
.mini-action:hover { border-color: #3b82f6; color: #3b82f6; }
.mini-action.danger:hover { border-color: #ef4444; color: #ef4444; }
.preset-btn { padding: 6px 12px; font-size: 12px; border: 1px solid var(--border-color-strong); background: var(--bg-card); color: var(--text-secondary); border-radius: 8px; cursor: pointer; transition: all 0.2s; }
.preset-btn:hover { border-color: #3b82f6; color: #3b82f6; }
</style>