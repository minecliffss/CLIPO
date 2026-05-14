#!/bin/bash
cd "$(dirname "$0")"
source ../venv/bin/activate
../venv/bin/python server.py
