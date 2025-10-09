@echo off
echo ======================================
echo Restarting ADK with API Key
echo ======================================
docker-compose down adk
docker-compose up -d adk
echo.
echo ✓ ADK restarted!
echo.
echo Waiting for ADK to start...
timeout /t 10 /nobreak >nul
echo.
echo ✓ ADK should be ready at: http://localhost:7860
echo.
docker logs data-warehouse-adk-1 --tail 20
