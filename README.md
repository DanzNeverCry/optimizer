# DanzSuperOptimizer v1.0.0

System optimizer untuk Windows 10/11. Tema Black + Mazda Soul Red.
Dibangun dengan PySide6 (Qt resmi, lisensi LGPL — boleh dijual sebagai
aplikasi tertutup, beda dengan PyQt6 yang GPLv3).

## Cara mendapatkan file .exe

Compile ke `.exe` Windows harus dilakukan di mesin Windows (atau runner
Windows) — tidak bisa di-cross-compile dari Linux/Mac. Dua cara:

### Cara A — otomatis, tanpa install apa pun (disarankan)

1. Push folder ini ke repo GitHub baru.
2. GitHub akan otomatis menjalankan `.github/workflows/build.yml` di mesin
   Windows cloud setiap kali kamu push ke branch `main`.
3. Buka tab **Actions** di repo -> klik run terbaru -> download artifact
   **DanzSuperOptimizer-exe**. Isinya `DanzSuperOptimizer.exe` siap pakai.
4. Bisa juga dipicu manual lewat tombol **Run workflow** (tanpa push baru).

### Cara B — build manual di Windows kamu sendiri

1. Install Python 3.9+ (centang "Add to PATH") di Windows.
2. Klik dua kali `build.bat`.
3. Hasil ada di `dist\DanzSuperOptimizer.exe` — satu file, embed Python,
   otomatis minta hak Administrator saat dibuka.

## Jalankan langsung tanpa build (untuk testing)

```
pip install -r requirements.txt
python danzsuperoptimizer.py
```
atau klik kanan `run.bat` -> Run as administrator.

## Isi layar

| Box | Isi |
|-----|-----|
| 1 (kiri atas) | Gauge + grafik live RAM & CPU |
| 4 (kanan atas) | Daftar opsi RAM optimizer, CPU optimizer, signal booster |
| 3 (kanan bawah) | Grafik throughput jaringan + ping/download/upload + speed test |
| 2 (bawah) | Aplikasi background + tombol END per aplikasi |

## RAM Optimizer

Delapan rutin, memanggil `NtSetSystemInformation` langsung seperti Mem Reduct:

| Opsi | API |
|------|-----|
| Modified file cache | `SystemFileCacheInformationEx` |
| Modified page list | `MemoryFlushModifiedList` |
| Standby list | `MemoryPurgeStandbyList` |
| Standby list (without priority) | `MemoryPurgeLowPriorityStandbyList` |
| Registry cache (Win 8.1+) | `SystemRegistryQuotaInformation` |
| Combine memory lists (Win 10+) | `SystemCombinePhysicalMemoryInformation` |
| Working set | `MemoryEmptyWorkingSets` + `EmptyWorkingSet` per proses |
| System file cache | `SystemFileCacheInformation` |

**OPTIMIZE ALL** menjalankan kedelapannya berurutan, lalu keluar notifikasi
jumlah GB/MB RAM yang dibebaskan (dihitung dari selisih `GlobalMemoryStatusEx`
sebelum dan sesudah). Wajib Administrator — tanpa itu sebagian rutin gagal.

## CPU Optimizer

Dialog peringatan berisi daftar aplikasi yang akan ditutup dulu, baru layar
jadi hitam sampai selesai. Dilindungi: PID <= 4, semua executable di dalam
`C:\Windows`, proses milik SYSTEM/LOCAL SERVICE/NETWORK SERVICE, dan daftar
nama kritikal (csrss, wininit, winlogon, services, lsass, svchost, dwm,
explorer, spoolsv, ctfmon, sihost, RuntimeBroker, SearchHost, MsMpEng,
SecurityHealthService, dll). Discord/Spotify/dll tertutup, Windows tetap aman.

## Signal Booster

Menjalankan `ipconfig /flushdns`, `/registerdns`, hapus ARP cache, refresh
status TCP/Winsock. **Tidak bisa menaikkan bandwidth di atas paket ISP atau
memperkuat sinyal WiFi/seluler** — ini ditulis apa adanya di UI. Speed
test-nya asli (endpoint Cloudflare).

## Sebelum dijual

- **Code signing**: tanpa sertifikat, Windows SmartScreen akan menandai
  "Unknown publisher" dan antivirus bisa false-positive karena aplikasi ini
  mematikan proses & menyentuh API memori kernel. Untuk jual publik,
  pertimbangkan OV code signing certificate atau Azure Trusted Signing.
- **Klaim jualan**: jangan tulis "boost kecepatan internet" — booster di
  sini hanya refresh cache, bukan penambah bandwidth. Jual dengan klaim yang
  memang benar: monitoring real-time, pembersihan memori, end-task
  background, network refresh, speed test.
- **Installer**: `dist\DanzSuperOptimizer.exe` bisa dibungkus Inno Setup
  kalau mau ada Start Menu shortcut + uninstaller.
