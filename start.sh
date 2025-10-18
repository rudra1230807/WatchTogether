#!/bin/bash
# Install dependencies first
pip install --upgrade pip
pip install -r requirements.txt

# Start FastAPI in background
uvicorn server:app --host 0.0.0.0 --port 8000 &

# Start Streamlit
streamlit run App.py --server.port 8501 --server.address 0.0.0.0
