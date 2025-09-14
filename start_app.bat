@echo off
echo Starting AI Companion Application...

REM Clean up any existing containers
docker stop qdrant-local 2>nul
docker rm qdrant-local 2>nul

REM Start Qdrant
echo Starting Qdrant...
docker run -d --name qdrant-local -p 6334:6333 -v "%CD%/qdrant_storage:/qdrant/storage" qdrant/qdrant

REM Wait for Qdrant to start
echo Waiting for Qdrant to be ready...
timeout /t 5

REM Check if Qdrant is running
docker ps | findstr qdrant-local
if errorlevel 1 (
    echo Failed to start Qdrant
    pause
    exit /b 1
)

echo Qdrant started successfully!
echo Access Qdrant dashboard at: http://localhost:6334/dashboard

REM Start Chainlit (you'll need to create the chainlit app first)
echo Starting Chainlit...
echo You can now run: python -m chainlit run src/ai_companion/interfaces/chainlit_app.py

pause