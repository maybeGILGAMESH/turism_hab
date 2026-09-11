# Мобильный клиент «Открой Хабаровский край»

```powershell
# API должен работать на localhost:8000
..\start-mobile-web.ps1

# Для установленного AVD Khabarovsk_Pixel_7
..\start-android.ps1
```

Expo Web использует `localhost`, Android Emulator — `10.0.2.2`. Для физического телефона задайте `EXPO_PUBLIC_API_BASE_URL=http://<LAN-IP>:8000` или сохраните URL на экране настроек.
