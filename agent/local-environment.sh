set -e # exit when any command fails

SCRIPT_DIR="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

echo "Stopping existing containers..."
docker-compose -f "$SCRIPT_DIR/docker-compose.yml" down --volumes

echo "Starting application..."
docker-compose -f "$SCRIPT_DIR/docker-compose.yml" up -d --build

# Note: Database migrations run automatically via start.sh script
# No manual migration step needed

echo "Application started successfully!"
echo "API available at: http://localhost:8000"
