@echo off
echo Starting the Geo-Compliance Classifier Streamlit app...

:: Activate the virtual environment
:: Change the path to your own venv path example: venvloc\Scripts\activate.bat
call tiktokvenv\Scripts\activate.bat

:: Run Streamlit in the background
start /B streamlit run app.py --server.headless=false

:: Wait a moment for the server to start
timeout /t 3 > nul

:: Open the browser automatically using start command
::start http://172.20.10.6:8501/

echo Application started in your browser.
pause