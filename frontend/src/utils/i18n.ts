import { readonly, ref } from 'vue'
import type { UISettings } from '../api/types/settings'

export type Locale = UISettings['language']

const STORAGE_KEY = 'neo-mofox-locale'
const DEFAULT_LOCALE: Locale = 'zh-CN'

const messages = {
  'zh-CN': {
    app: {
      nav: {
        home: '主页',
        config: '配置',
        plugins: '插件',
        settings: '设置',
      },
      actions: {
        restart: '重启',
        shutdown: '关闭',
        logout: '退出',
      },
      aria: {
        goHome: '导航到主页',
        restartSystem: '重启系统',
        shutdownSystem: '关闭系统',
        logout: '退出登录',
        closeNav: '关闭导航',
        openMenu: '打开菜单',
      },
      dialogs: {
        restartTitle: '确认重启',
        restartMessage: '确定要重启 Bot 系统吗？',
        restartConfirm: '重启',
        shutdownTitle: '确认关闭',
        shutdownMessage: '确定要关闭 Bot 系统吗？关闭后需要手动重启。',
        shutdownConfirm: '关闭',
        cancel: '取消',
        restartingTitle: '系统重启中',
        restartingMessage: '正在重启 Bot 系统，请稍候...\n\n该对话框将在系统重启成功后自动关闭。',
      },
      toast: {
        restartSuccess: '系统重启成功',
        restartFailed: '重启失败，请稍后重试',
        shutdownSent: '关闭指令已发送',
        shutdownFailed: '关闭失败，请稍后重试',
      },
    },
    routes: {
      home: '主页',
      config: '配置管理',
      'config-plugins': '插件配置',
      'settings-theme': '主题设置',
      'settings-general': '通用设置',
      'settings-data': '数据管理',
      settings: '设置',
    },
    settings: {
      title: '设置',
      tabs: {
        theme: '主题',
        general: '通用',
        data: '数据',
      },
      general: {
        title: '通用设置',
        subtitle: '调整界面语言、字体与系统行为偏好',
        autosave: '修改后自动保存',
        loading: '加载配置中…',
        interfaceTitle: '界面',
        interfaceDesc: '语言和字体大小等显示相关选项',
        languageLabel: '界面语言',
        languageHint: '选择 WebUI 的显示语言',
        languageZh: '简体中文',
        languageEn: 'English',
        fontSizeLabel: '字体大小',
        fontSizeHint: '调整文字显示尺寸',
        fontSmall: '小',
        fontMedium: '中',
        fontLarge: '大',
        systemTitle: '系统',
        systemDesc: '更新检查等后台行为选项',
        autoUpdate: '自动更新',
        autoUpdateHint: '发现新版本后自动下载并安装',
        checkUpdateOnStartup: '启动时检查更新',
        checkUpdateOnStartupHint: '每次启动时自动检测是否有新版本',
        refetch: '重新获取',
        reset: '恢复默认',
        resetDone: '已重置为默认设置',
        devBackendOfflineUnsaved: '[DEV] 后端未启动，更改不会持久化',
        devBackendOfflineDefaults: '[DEV] 后端未启动，使用默认配置',
        devBackendOffline: '[DEV] 后端未启动',
      },
    },
  },
  'en-US': {
    app: {
      nav: {
        home: 'Home',
        config: 'Config',
        plugins: 'Plugins',
        settings: 'Settings',
      },
      actions: {
        restart: 'Restart',
        shutdown: 'Shutdown',
        logout: 'Logout',
      },
      aria: {
        goHome: 'Go to home',
        restartSystem: 'Restart system',
        shutdownSystem: 'Shutdown system',
        logout: 'Log out',
        closeNav: 'Close navigation',
        openMenu: 'Open menu',
      },
      dialogs: {
        restartTitle: 'Confirm Restart',
        restartMessage: 'Restart the Bot system?',
        restartConfirm: 'Restart',
        shutdownTitle: 'Confirm Shutdown',
        shutdownMessage: 'Shut down the Bot system? You will need to restart it manually.',
        shutdownConfirm: 'Shutdown',
        cancel: 'Cancel',
        restartingTitle: 'Restarting System',
        restartingMessage: 'Restarting the Bot system. Please wait...\n\nThis dialog will close automatically after the system restarts.',
      },
      toast: {
        restartSuccess: 'System restarted successfully',
        restartFailed: 'Restart failed. Please try again later.',
        shutdownSent: 'Shutdown command sent',
        shutdownFailed: 'Shutdown failed. Please try again later.',
      },
    },
    routes: {
      home: 'Home',
      config: 'Config Management',
      'config-plugins': 'Plugin Config',
      'settings-theme': 'Theme Settings',
      'settings-general': 'General Settings',
      'settings-data': 'Data Management',
      settings: 'Settings',
    },
    settings: {
      title: 'Settings',
      tabs: {
        theme: 'Theme',
        general: 'General',
        data: 'Data',
      },
      general: {
        title: 'General Settings',
        subtitle: 'Adjust interface language, font size, and system behavior preferences',
        autosave: 'Changes are saved automatically',
        loading: 'Loading settings…',
        interfaceTitle: 'Interface',
        interfaceDesc: 'Display options such as language and font size',
        languageLabel: 'Interface Language',
        languageHint: 'Choose the display language for WebUI',
        languageZh: '简体中文',
        languageEn: 'English',
        fontSizeLabel: 'Font Size',
        fontSizeHint: 'Adjust text display size',
        fontSmall: 'Small',
        fontMedium: 'Medium',
        fontLarge: 'Large',
        systemTitle: 'System',
        systemDesc: 'Background behavior options such as update checks',
        autoUpdate: 'Auto Update',
        autoUpdateHint: 'Automatically download and install new versions when available',
        checkUpdateOnStartup: 'Check Updates on Startup',
        checkUpdateOnStartupHint: 'Automatically check for new versions on each startup',
        refetch: 'Reload',
        reset: 'Restore Defaults',
        resetDone: 'Restored default settings',
        devBackendOfflineUnsaved: '[DEV] Backend is not running. Changes will not persist.',
        devBackendOfflineDefaults: '[DEV] Backend is not running. Using default settings.',
        devBackendOffline: '[DEV] Backend is not running.',
      },
    },
  },
} as const

const savedLocale = localStorage.getItem(STORAGE_KEY)
const locale = ref<Locale>(isLocale(savedLocale) ? savedLocale : DEFAULT_LOCALE)

function isLocale(value: unknown): value is Locale {
  return value === 'zh-CN' || value === 'en-US'
}

function resolveMessage(localeValue: Locale, key: string): string | undefined {
  return key.split('.').reduce<unknown>((current, segment) => {
    if (current && typeof current === 'object' && segment in current) {
      return (current as Record<string, unknown>)[segment]
    }
    return undefined
  }, messages[localeValue]) as string | undefined
}

export function setLocale(nextLocale: Locale) {
  locale.value = nextLocale
  localStorage.setItem(STORAGE_KEY, nextLocale)
  document.documentElement.lang = nextLocale
}

export function t(key: string): string {
  return resolveMessage(locale.value, key) ?? resolveMessage(DEFAULT_LOCALE, key) ?? key
}

export function useI18n() {
  return {
    locale: readonly(locale),
    setLocale,
    t,
  }
}

setLocale(locale.value)
