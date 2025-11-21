"""
Configuration for the process module
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Parquet Configuration
PARQUET_BASE_PATH = os.getenv('PARQUET_BASE_PATH', 'data/parquet')
PARQUET_TABLE_NAME = os.getenv('PARQUET_TABLE_NAME', 'recommendation_events')
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '10'))

