# Quick Docker Reference

## Start xCode Stack

```bash
./docker-start.sh
# or
make start
```

## Run xCode

```bash
make xcode
# or
docker-compose run --rm xcode
```

## Common Commands

```bash
make up          # Start backend services
make down        # Stop all services
make logs        # View logs
make health      # Check service status
make test        # Run tests
```

## Service URLs

- **Neo4j Browser**: http://localhost:7474 (neo4j/password)
- **xCode Agent API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Troubleshooting

### Docker Registry Timeout
If `docker-compose up` times out, use `./docker-start.sh` which has retry logic.

### Services Not Healthy
```bash
# Check logs
docker-compose logs xcode-agent
docker-compose logs neo4j

# Restart
docker-compose restart
```

### Clean Start
```bash
make clean  # Removes volumes
make build  # Rebuild images
make up     # Start fresh
```

See DOCKER.md for full documentation.
