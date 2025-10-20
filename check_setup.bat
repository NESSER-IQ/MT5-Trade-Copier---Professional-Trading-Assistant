@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
echo ========================================
echo فحص إعداد النظام
echo System Setup Check
echo ========================================
echo.
python check_setup.py
