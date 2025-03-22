#!/bin/bash

# Lancer Uvicorn avec asgi_app
exec uvicorn campaign_analyst:asgi_app --host 0.0.0.0 --port $PORT
