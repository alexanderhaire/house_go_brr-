@echo off
echo Starting House Discovery Engine...

:: Set Environment Variables
set "OPENAI_API_KEY=<YOUR_OPENAI_KEY_HERE>"
set "RENTCAST_API_KEY=<YOUR_RENTCAST_KEY_HERE>"
set "MORTGAGE_INTEREST_RATE=0.06"

:: Run the python daemon
python -u main.py

pause
