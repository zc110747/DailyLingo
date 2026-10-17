@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo  DailyLingo - auto rebuild on content change
echo ============================================
echo.

if not exist "scripts\watch.py" goto no_script

set "PY="
where py >nul 2>&1
if not errorlevel 1 set "PY=py -3"
if defined PY goto have_python

where python >nul 2>&1
if not errorlevel 1 set "PY=python"
if defined PY goto have_python

goto no_python

:have_python
echo Interpreter : %PY%
echo Watching    : content\*.md  sources\*.wav
echo Rebuilds    : index.html + src\*.html
echo Audio       : EnglishAudio (eaudio.cmd) for any missing wav
echo.
echo The resolved EnglishAudio path is printed below. To use a specific copy, set
echo   DAILYLINGO_AUDIO_TOOL, or run watch.py with --audio-tool "path\to\eaudio.cmd".
echo.
echo Press Ctrl+C to stop.
echo.

%PY% "scripts\watch.py" --audio
if errorlevel 1 goto watch_failed

echo.
echo [OK] Watcher stopped.
echo.
pause
exit /b 0

:no_python
echo [FAIL] Python 3 was not found in PATH.
echo        Install Python 3, or run the watcher manually, for example:
echo          python scripts\watch.py --audio
echo.
pause
exit /b 1

:no_script
echo [FAIL] scripts\watch.py was not found next to this script.
echo        Run this file from the DailyLingo project root.
echo.
pause
exit /b 1

:watch_failed
echo [FAIL] The watcher exited with an error. See the messages above.
echo.
pause
exit /b 1
