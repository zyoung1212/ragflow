#!/bin/bash

# Production service launcher for RAGFlow
# This script starts RAGFlow in production mode using Gunicorn

set -e

echo "=========================================="
echo "RAGFlow Production Service Launcher"
echo "=========================================="

# Function to load environment variables from .env file
load_env_file() {
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local env_file="$script_dir/.env"

    if [ -f "$env_file" ]; then
        echo "Loading environment variables from: $env_file"
        set -a
        source "$env_file" 
        set +a
    else
        echo "Warning: .env file not found at: $env_file"
    fi
}

# Load environment variables
load_env_file

# Unset HTTP proxies that might be set by Docker daemon
export http_proxy=""; export https_proxy=""; export no_proxy=""; export HTTP_PROXY=""; export HTTPS_PROXY=""; export NO_PROXY=""
export PYTHONPATH=$(pwd)

export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/
JEMALLOC_PATH=$(pkg-config --variable=libdir jemalloc)/libjemalloc.so

PY=python3

# Set default number of workers if WS is not set or less than 1
if [[ -z "$WS" || $WS -lt 1 ]]; then
  WS=1
fi

# Set default number of Gunicorn workers
if [[ -z "$GUNICORN_WORKERS" ]]; then
  GUNICORN_WORKERS=$(($(nproc) * 2 + 1))
fi

# Maximum number of retries for each task executor and server
MAX_RETRIES=5

# Flag to control termination
STOP=false

# Array to keep track of child PIDs
PIDS=()

# Set the path to the NLTK data directory
export NLTK_DATA="./nltk_data"

# Function to handle termination signals
cleanup() {
  echo "Termination signal received. Shutting down..."
  STOP=true
  # Terminate all child processes
  for pid in "${PIDS[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then
      echo "Killing process $pid"
      kill "$pid"
    fi
  done
  exit 0
}

# Trap SIGINT and SIGTERM to invoke cleanup
trap cleanup SIGINT SIGTERM

# Function to execute task_executor with retry logic
task_exe(){
    local task_id=$1
    local retry_count=0
    while ! $STOP && [ $retry_count -lt $MAX_RETRIES ]; do
        echo "Starting task_executor.py for task $task_id (Attempt $((retry_count+1)))"
        LD_PRELOAD=$JEMALLOC_PATH $PY rag/svr/task_executor.py "$task_id"
        EXIT_CODE=$?
        if [ $EXIT_CODE -eq 0 ]; then
            echo "task_executor.py for task $task_id exited successfully."
            break
        else
            echo "task_executor.py for task $task_id failed with exit code $EXIT_CODE. Retrying..." >&2
            retry_count=$((retry_count + 1))
            sleep 2
        fi
    done

    if [ $retry_count -ge $MAX_RETRIES ]; then
        echo "task_executor.py for task $task_id failed after $MAX_RETRIES attempts. Exiting..." >&2
        cleanup
    fi
}

# Function to execute ragflow_server with Gunicorn
run_production_server(){
    local retry_count=0
    while ! $STOP && [ $retry_count -lt $MAX_RETRIES ]; do
        echo "Starting RAGFlow server in production mode with Gunicorn (Workers: $GUNICORN_WORKERS, Attempt: $((retry_count+1)))"
        echo "Server will be available at: http://0.0.0.0:${HOST_PORT:-9380}"
        
        # Export environment variables for Gunicorn config
        export GUNICORN_WORKERS
        
        gunicorn -c gunicorn_config.py api.wsgi:application
        EXIT_CODE=$?
        
        if [ $EXIT_CODE -eq 0 ]; then
            echo "RAGFlow server exited successfully."
            break
        else
            echo "RAGFlow server failed with exit code $EXIT_CODE. Retrying..." >&2
            retry_count=$((retry_count + 1))
            sleep 2
        fi
    done

    if [ $retry_count -ge $MAX_RETRIES ]; then
        echo "RAGFlow server failed after $MAX_RETRIES attempts. Exiting..." >&2
        cleanup
    fi
}

echo "Production Mode Configuration:"
echo "  - Task Executor Workers: $WS"
echo "  - Gunicorn Workers: $GUNICORN_WORKERS"
echo "  - Host Port: ${HOST_PORT:-9380}"
echo "  - Python Path: $PYTHONPATH"
echo "=========================================="

# Start task executors
echo "Starting $WS task executor(s)..."
for ((i=0;i<WS;i++))
do
  task_exe "$i" &
  PIDS+=($!)
done

# Start the main server with Gunicorn
run_production_server &
PIDS+=($!)

echo "All services started. Waiting for processes..."

# Wait for all background processes to finish
wait 