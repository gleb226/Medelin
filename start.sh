#!/bin/bash

# Start the combined bot and API process
python bot.py &

# Wait a bit for services to start
sleep 5

# Start Nginx
nginx -g "daemon off;"