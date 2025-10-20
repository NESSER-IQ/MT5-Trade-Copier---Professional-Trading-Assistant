@echo off
echo ========================================
echo   رفع المشروع إلى GitHub
echo ========================================
echo.

REM التحقق من وجود Git
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Git غير مثبت!
    echo قم بتحميله من: https://git-scm.com/download/win
    pause
    exit /b
)

REM إنشاء .gitignore إذا لم يكن موجوداً
if not exist .gitignore (
    echo إنشاء ملف .gitignore...
    (
        echo # بيانات حساسة
        echo data/*.enc
        echo data/*.key
        echo data/settings.json
        echo data/channels.json
        echo *.session
        echo .env
        echo.
        echo # Python
        echo __pycache__/
        echo *.pyc
        echo .venv/
        echo venv/
        echo.
        echo # OS
        echo .DS_Store
        echo Thumbs.db
    ) > .gitignore
)

REM تهيئة Git
if not exist .git (
    echo تهيئة Git...
    git init
    git branch -M main
)

REM إضافة جميع الملفات
echo إضافة الملفات...
git add .

REM عرض الملفات المضافة
echo.
echo الملفات التي سيتم رفعها:
git status --short
echo.

REM التأكيد
set /p confirm="هل تريد المتابعة؟ (y/n): "
if /i not "%confirm%"=="y" (
    echo تم الإلغاء
    pause
    exit /b
)

REM Commit
echo.
set /p message="أدخل رسالة الـ commit (اتركه فارغ للرسالة الافتراضية): "
if "%message%"=="" set message=Initial commit - MT5 Trade Copier with fixes

git commit -m "%message%"

REM إضافة الـ remote
echo.
echo إضافة المستودع...
set remote=https://github.com/NESSER-IQ/MT5-Trade-Copier---Professional-Trading-Assistant.git

git remote add origin %remote% 2>nul
git remote set-url origin %remote%

REM Push
echo.
echo جاري الرفع...
git push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo ✅ تم الرفع بنجاح!
    echo ========================================
    echo.
    echo يمكنك الآن زيارة مستودعك:
    echo %remote%
    echo.
) else (
    echo.
    echo ========================================
    echo ❌ حدث خطأ أثناء الرفع
    echo ========================================
    echo.
    echo تأكد من:
    echo 1. رابط المستودع صحيح
    echo 2. لديك صلاحيات الوصول
    echo 3. قمت بتسجيل الدخول في Git
    echo.
    echo لتسجيل الدخول، استخدم:
    echo git config --global user.name "اسمك"
    echo git config --global user.email "بريدك@example.com"
    echo.
    echo ثم شغّل هذا الملف مرة أخرى
)

echo.
pause