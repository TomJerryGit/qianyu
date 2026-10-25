@echo off
cd /d D:\qianyu\tools\jellyfin-server\jellyfin
echo Starting local Jellyfin on http://127.0.0.1:8096
echo Test user: qianyu / qianyu-test-pass
echo Keep this window open. Press Ctrl+C to stop.
jellyfin.exe --datadir D:\qianyu\tools\jellyfin-test-data --configdir D:\qianyu\tools\jellyfin-test-config --cachedir D:\qianyu\tools\jellyfin-test-cache --logdir D:\qianyu\tools\jellyfin-test-logs
pause
