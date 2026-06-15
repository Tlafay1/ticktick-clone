import type { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'com.ticktick.clone',
  appName: 'TickTick Clone',
  webDir: '../web/dist',
  server: {
    // En dev, pointer sur le vite dev server pour le HMR
    // url: 'http://10.0.2.2:5173',
    // cleartext: true,
  },
  plugins: {
    LocalNotifications: {
      smallIcon: 'ic_stat_icon_config_sample',
      iconColor: '#4772fa',
      sound: 'beep.wav',
    },
    CapacitorHttp: {
      enabled: true,
    },
  },
  android: {
    allowMixedContent: false,
    captureInput: true,
    webContentsDebuggingEnabled: false,
  },
}

export default config
