# Process Module

This module processes messages from RabbitMQ, transforms them, and stores them in Parquet format.

## Architecture

```
RabbitMQ Queue → Consumer → Transformer → Parquet Writer → Parquet Files
```

## Components

### MessageProcessor
Main orchestrator that:
- Consumes messages from RabbitMQ
- Transforms messages (adds `hit_flink` field)
- Writes transformed messages to Parquet in batches

### MessageTransformer
Transforms messages by adding the `hit_flink: true` field to each message.

### ParquetWriter
Writes messages to Parquet format with:
- Partitioning by date (year/month/day)
- Snappy compression
- Columnar storage format

## Usage

### Start the Processor

```bash
python process/processor.py
```

Or programmatically:

```python
from process.processor import MessageProcessor

processor = MessageProcessor(
    parquet_base_path="data/parquet",
    parquet_table_name="recommendation_events",
    batch_size=10
)

processor.start()
```

## Configuration

Create a `.env` file or set environment variables:

```
PARQUET_BASE_PATH=data/parquet
PARQUET_TABLE_NAME=recommendation_events
BATCH_SIZE=10
```

## Output Format

Messages are stored in Parquet format with the following schema:

```json
{
    "user_id": "string",
    "item_id": "string",
    "process_time": 1234567890.123,
    "hit_flink": true
}
```

Files are partitioned by date:
```
data/parquet/recommendation_events/
  year=2025/
    month=11/
      day=20/
        part-20251120_123456_123456.parquet
```

## Reading Data

You can read the stored data using pandas:

```python
from process.parquet_writer import ParquetWriter

writer = ParquetWriter()
df = writer.read_partition(year=2025, month=11, day=20)
print(df)
```

