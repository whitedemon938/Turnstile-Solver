# Use an official Python base image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Install patchright
RUN pip install --no-cache-dir patchright && patchright install chromium

# Copy the rest of the application files
COPY . .


# Run the application
CMD ["python3", "main.py"]
