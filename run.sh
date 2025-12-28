#!/bin/bash
export PYTHONPATH=$PYTHONPATH:$(pwd)
python3 -m streamlit run app/main.py
