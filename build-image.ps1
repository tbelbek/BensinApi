# Build the Docker image
docker build -t bensinpriser .

# Tag the Docker image
docker tag bensinpriser tbelbek/bensinpriser:latest

# Push the Docker image to the registry
docker push tbelbek/bensinpriser:latest

# Pull the latest images defined in the docker-compose.yml file
docker-compose pull

# Start the services defined in the docker-compose.yml file in detached mode
docker-compose up -d