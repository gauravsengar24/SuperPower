"""Streamlit Cloud entry point for T.R.E.N.D. dashboard.

Auto-detected by Streamlit Cloud at deploy time.
Usage: streamlit run streamlit_app.py
"""

import os
import sys

# Ensure the trading package is importable
sys.path.insert(0, os.path.dirname(__file__))

from trading.monitoring.dashboard import run_dashboard

if __name__ == "__main__":
    run_dashboard()
