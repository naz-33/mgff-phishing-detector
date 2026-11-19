#!/usr/bin/env python3
"""Run script for ZanderEtAlFishing Web Dashboard Backend API.

Launches the FastAPI application on http://127.0.0.1:8000 serving both the API
and the built React frontend.
"""

import argparse
import sys
import uvicorn


def main():
    parser = argparse.ArgumentParser(description="ZanderEtAlFishing Dashboard Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload on code change")
    args = parser.parse_args()

    print("========================================")
    print("           ZanderEtAlFishing")
    print("      WEB MONITORING DASHBOARD")
    print("========================================")
    print(f"API Server: http://{args.host}:{args.port}/api")
    print(f"API Docs:   http://{args.host}:{args.port}/docs")
    print(f"Dashboard:  http://{args.host}:{args.port}/")
    print("========================================")

    uvicorn.run("backend.app:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()

