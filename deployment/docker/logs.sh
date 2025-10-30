#!/bin/bash
##
## View Logs for Docker Deployment
##

# Default to trader service if no argument provided
SERVICE=${1:-trader}

echo "Viewing logs for: $SERVICE"
echo "Press Ctrl+C to exit"
echo ""

docker-compose logs -f --tail=100 $SERVICE
