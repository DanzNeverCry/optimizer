# DÄNZ OPTIMIZER v1.0

System optimizer untuk Windows 10/11. Tema Black + Mazda Soul Red.

## Cara pakai (cepat)

1. Install Python 3.9+ (centang "Add to PATH").
2. Klik kanan `run.bat` → Run as administrator. Script akan otomatis minta elevasi.

Manual:
```
pip install -r requirements.txt
python app.py
```

## Jadikan .exe untuk dibagikan

Klik dua kali `build.bat`. Hasilnya di `dist\DANZ Optimizer.exe` — satu file,
tanpa Python, dan otomatis meminta hak Administrator saat dibuka.

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

**OPTIMIZE ALL** menjalankan kedelapannya berurutan. Setelah selesai muncul
notifikasi berisi jumlah GB/MB RAM yang dibebaskan (dihitung dari selisih
`GlobalMemoryStatusEx` sebelum dan sesudah).

Wajib Administrator — tanpa itu privilege `SeProfileSingleProcess` dan
`SeIncreaseQuota` tidak bisa diaktifkan dan sebagian rutin akan gagal
(aplikasi tetap jalan, hanya melapor rutin mana yang gagal).

## CPU Optimizer

Menampilkan dialog peringatan berisi daftar aplikasi yang akan ditutup, lalu
layar menjadi hitam sampai proses selesai.

Yang dilindungi dan **tidak pernah** ditutup:
- PID ≤ 4, proses aplikasi ini sendiri
- Semua executable di dalam `C:\Windows`
- Proses milik SYSTEM / LOCAL SERVICE / NETWORK SERVICE
- Daftar nama kritikal: `csrss, wininit, winlogon, services, lsass, svchost,
  dwm, explorer, spoolsv, ctfmon, sihost, RuntimeBroker, SearchHost,
  MsMpEng, SecurityHealthService`, dll.

Jadi Discord, Spotify, Chrome, launcher game dsb. tertutup, sementara Windows
tetap berjalan normal.

## Signal Booster

Menjalankan `ipconfig /flushdns`, `/registerdns`, hapus ARP cache, dan refresh
status TCP/Winsock. Ini membantu kalau koneksi tersendat karena cache DNS basi,
tapi **tidak bisa menaikkan bandwidth di atas paket ISP atau memperkuat sinyal
WiFi/seluler** — hal itu sudah ditulis apa adanya di dalam UI supaya pengguna
tidak salah paham. Speed test-nya asli (endpoint Cloudflare), jadi hasil
sebelum/sesudah bisa dibandingkan sendiri.

## Catatan distribusi

Antivirus kadang menandai .exe PyInstaller yang mematikan proses sebagai
false positive. Untuk publikasi luas, sebaiknya tanda tangani .exe dengan
code signing certificate, atau bagikan dalam bentuk source + `run.bat`.
