#!/bin/bash

# Navigate to the project root directory
cd "$(dirname "$0")"

uvicorn run:run --host 0.0.0.0 --port 8000
