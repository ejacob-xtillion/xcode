#!/bin/bash
set -e

echo "🚀 Starting xCode Docker Stack"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop."
    exit 1
fi

echo "📦 Pulling Neo4j image (this may take a while on first run)..."
docker pull neo4j:5.15 || {
    echo "⚠️  Failed to pull Neo4j image. Retrying..."
    sleep 5
    docker pull neo4j:5.15
}

echo ""
echo "🔨 Building xCode Agent..."
docker-compose build xcode-agent

echo ""
echo "🔨 Building xCode CLI..."
docker-compose build xcode

echo ""
echo "🚀 Starting services..."
docker-compose up -d neo4j xcode-agent

echo ""
echo "⏳ Waiting for services to be healthy..."
echo "   This may take up to 60 seconds..."

# Wait for Neo4j
echo -n "   Neo4j: "
for i in {1..30}; do
    if docker-compose exec -T neo4j cypher-shell -u neo4j -p password "RETURN 1" > /dev/null 2>&1; then
        echo "✓ Ready"
        break
    fi
    echo -n "."
    sleep 2
done

# Wait for xCode Agent
echo -n "   xCode Agent: "
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✓ Ready"
        break
    fi
    echo -n "."
    sleep 2
done

echo ""
echo "✅ All services ready!"
echo ""
echo "📊 Service Status:"
docker-compose ps
echo ""
echo "🎯 Next Steps:"
echo "   • Run xCode:        docker-compose run --rm xcode"
echo "   • View logs:        docker-compose logs -f"
echo "   • Stop services:    docker-compose down"
echo "   • Or use Makefile:  make xcode"
echo ""
