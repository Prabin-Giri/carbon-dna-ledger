#!/bin/bash
cd /Users/bipinsapkota/Downloads/CarbonDNAReport
python3 -m uvicorn app.main:app --reload --port 8000 --host 127.0.0.1
