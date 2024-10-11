@echo off
call conda.bat activate joris-env
if %ERRORLEVEL% neq 0 (
    echo Failed to activate Conda environment
    pause
    exit /b %ERRORLEVEL%
)

npm start
if %ERRORLEVEL% neq 0 (
    echo Failed to start the application
    pause
    exit /b %ERRORLEVEL%
)

pause