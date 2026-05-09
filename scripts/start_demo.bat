@echo off
setlocal

set "PROJECT_ROOT=%~dp0.."
set "CONDA_ENV=wordplugin"

cd /d "%PROJECT_ROOT%"

where conda >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    call conda activate %CONDA_ENV%
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to activate conda environment "%CONDA_ENV%".
        echo Make sure the environment exists, or edit scripts\start_demo.bat.
        pause
        exit /b 1
    )
) else (
    if exist "%USERPROFILE%\anaconda3\Scripts\activate.bat" (
        call "%USERPROFILE%\anaconda3\Scripts\activate.bat" %CONDA_ENV%
    ) else if exist "%USERPROFILE%\miniconda3\Scripts\activate.bat" (
        call "%USERPROFILE%\miniconda3\Scripts\activate.bat" %CONDA_ENV%
    ) else if exist "E:\Applications\Anaconda3\Scripts\activate.bat" (
        call "E:\Applications\Anaconda3\Scripts\activate.bat" %CONDA_ENV%
    ) else (
        echo Could not find conda.
        echo Open Anaconda Prompt, activate "%CONDA_ENV%", then run:
        echo   powershell -ExecutionPolicy Bypass -File scripts\start_demo.ps1
        pause
        exit /b 1
    )
)

python -c "import sys; print('Python:', sys.executable)"
python -c "import fastapi, uvicorn, openai, pydantic, httpx" >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Missing Python dependencies in environment "%CONDA_ENV%".
    echo Run:
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%PROJECT_ROOT%\scripts\start_demo.ps1"

endlocal
