# Use the official Python image from the Docker Hub
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install the required packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Copy the templates folder
COPY templates/ templates/

# Install cron
RUN apt-get update && apt-get install -y cron

# Add the crontab file in the cron directory
COPY crontab /etc/cron.d/extract_prices_cron

# Give execution rights on the cron job
RUN chmod 0644 /etc/cron.d/extract_prices_cron

# Apply cron job
RUN crontab /etc/cron.d/extract_prices_cron

# Create the log file to be able to run tail
RUN touch /var/log/cron.log

# Run the command on container startup
CMD cron && tail -f /var/log/cron.log

# docker build -t bensinpriser .
# docker tag bensinpriser tbelbek/bensinpriser:latest
# docker push tbelbek/bensinpriser:latest