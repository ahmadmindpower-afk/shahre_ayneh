@echo off
cd /d "%~dp0"
python tests\static_check.py
if errorlevel 1 exit /b 1
python tests\runtime_catalogue_check.py
if errorlevel 1 exit /b 1
python tests\city_world_check.py
if errorlevel 1 exit /b 1
python tests\job_space_regression.py
if errorlevel 1 exit /b 1
echo ALL_TESTS_OK
