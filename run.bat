@echo off
echo Building Docker image...
docker build -t mitosis-classifier .

echo Running Docker container...
docker run -it --rm -v "%cd%\input:/app/input" -v "%cd%\output:/app/output" mitosis-classifier
pause