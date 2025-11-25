@echo off
echo Running UV sync...
uv sync

echo.
echo Running Ruff check with ALL rules...
uv tool run ruff check --select ALL --exclude .venv

echo.
echo Running Ruff check with auto-fix...
uv tool run ruff check --fix --exclude .venv

echo.
echo Running pytest tests...
uv tool run pytest tests

echo.
echo All checks completed!
exit /b 0