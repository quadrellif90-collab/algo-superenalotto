@echo off
chcp 65001 >nul
powershell -ExecutionPolicy Bypass -WindowStyle Hidden -Command "& '%~dp0superenalotto_gui.ps1'"
