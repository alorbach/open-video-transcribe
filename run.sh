#!/bin/bash
if [ ! -f venv/bin/python ]; then
    echo "Virtual environment not found. Please run install.py first."
    exit 1
fi
source venv/bin/activate
python main.py

