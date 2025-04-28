# Use slim Python image
FROM python:3.10-slim

# Install OS-level dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-17-jdk \
    libgl1-mesa-glx \
    libglib2.0-0 \
    maven \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy ONLY requirements.txt first to leverage Docker cache
COPY requirements.txt .

# Install Python libraries (cached if requirements.txt does not change)
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the rest of your project
COPY . .

# Set default command (optional)
CMD ["python", "run_pipeline.py"]
