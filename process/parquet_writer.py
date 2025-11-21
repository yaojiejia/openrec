"""
Parquet Writer
Writes transformed messages to Parquet format
"""
import os
import logging
from typing import Dict, Any, List
from datetime import datetime
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ParquetWriter:
    """Writes data to Parquet format with date-based partitioning"""
    
    def __init__(self, base_path: str = "data/parquet", table_name: str = "recommendation_events"):
        """
        Initialize Parquet writer
        
        Args:
            base_path: Base path for Parquet storage
            table_name: Name of the Parquet table/dataset
        """
        self.base_path = base_path
        self.table_name = table_name
        self.table_path = os.path.join(base_path, table_name)
        
        # Create directory if it doesn't exist
        os.makedirs(self.table_path, exist_ok=True)
        
        logger.info(f"Initialized Parquet writer - Table: {table_name}, Path: {self.table_path}")
    
    def write(self, message: Dict[str, Any]) -> bool:
        """
        Write a single message to Parquet format
        
        Args:
            message: Transformed message to write
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Convert message to DataFrame
            df = pd.DataFrame([message])
            
            # Generate partition path based on timestamp (daily partitions)
            timestamp = message.get('process_time', datetime.now().timestamp())
            dt = datetime.fromtimestamp(timestamp)
            partition_path = os.path.join(
                self.table_path,
                f"year={dt.year}",
                f"month={dt.month:02d}",
                f"day={dt.day:02d}"
            )
            os.makedirs(partition_path, exist_ok=True)
            
            # Generate unique file name with timestamp
            file_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            file_path = os.path.join(partition_path, f"part-{file_timestamp}.parquet")
            
            # Write to Parquet
            df.to_parquet(
                file_path,
                engine='pyarrow',
                compression='snappy',
                index=False
            )
            
            logger.info(f"Message written to Parquet: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write message to Parquet: {e}")
            return False
    
    def write_batch(self, messages: List[Dict[str, Any]]) -> int:
        """
        Write a batch of messages to Parquet format
        
        Args:
            messages: List of transformed messages
        
        Returns:
            int: Number of successfully written messages
        """
        if not messages:
            return 0
        
        try:
            # Convert messages to DataFrame
            df = pd.DataFrame(messages)
            
            # Group by date for partitioning
            df['date'] = pd.to_datetime(df['process_time'], unit='s')
            df['year'] = df['date'].dt.year
            df['month'] = df['date'].dt.month
            df['day'] = df['date'].dt.day
            
            # Write each partition separately
            success_count = 0
            for (year, month, day), group in df.groupby(['year', 'month', 'day']):
                partition_path = os.path.join(
                    self.table_path,
                    f"year={year}",
                    f"month={month:02d}",
                    f"day={day:02d}"
                )
                os.makedirs(partition_path, exist_ok=True)
                
                # Remove partition columns before writing
                group_to_write = group.drop(columns=['date', 'year', 'month', 'day'])
                
                # Generate unique file name
                file_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                file_path = os.path.join(partition_path, f"part-{file_timestamp}.parquet")
                
                # Write to Parquet
                group_to_write.to_parquet(
                    file_path,
                    engine='pyarrow',
                    compression='snappy',
                    index=False
                )
                
                success_count += len(group_to_write)
                logger.info(f"Batch written to Parquet: {file_path} ({len(group_to_write)} messages)")
            
            return success_count
            
        except Exception as e:
            logger.error(f"Failed to write batch to Parquet: {e}")
            return 0
    
    def read_partition(self, year: int, month: int, day: int) -> pd.DataFrame:
        """
        Read messages from a specific partition
        
        Args:
            year: Year
            month: Month
            day: Day
        
        Returns:
            DataFrame with messages from that partition
        """
        partition_path = os.path.join(
            self.table_path,
            f"year={year}",
            f"month={month:02d}",
            f"day={day:02d}"
        )
        
        if not os.path.exists(partition_path):
            logger.warning(f"Partition does not exist: {partition_path}")
            return pd.DataFrame()
        
        try:
            # Read all Parquet files in the partition
            parquet_files = [
                os.path.join(partition_path, f)
                for f in os.listdir(partition_path)
                if f.endswith('.parquet')
            ]
            
            if not parquet_files:
                return pd.DataFrame()
            
            # Read and concatenate all files
            dfs = [pd.read_parquet(f) for f in parquet_files]
            return pd.concat(dfs, ignore_index=True)
            
        except Exception as e:
            logger.error(f"Failed to read partition: {e}")
            return pd.DataFrame()

