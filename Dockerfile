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

# Expose the necessary port (if applicable)
EXPOSE 8000  # Change this if your app runs on a different port

# Run the application
CMD ["python", "main.py"]
