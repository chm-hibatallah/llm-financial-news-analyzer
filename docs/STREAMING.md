# Real-Time Price Streaming Setup

This document explains how to run the real-time price streaming script to display today's prices on the Streamlit dashboard.

## Quick Start

### Step 1: Start the Price Stream

Open a new terminal and run:

```bash
python stream_prices.py
```

This script will:
- Continuously fetch 1-minute intraday prices for AAPL, TSLA, MSFT every 60 seconds
- Save prices to: `data/cache/intraday_prices.json`
- Display the latest price for each ticker
- Run for up to 90 hours (customize with `max_duration_hours` parameter)

### Step 2: View Prices on Dashboard

1. Keep the streaming script running
2. Open the Streamlit dashboard: http://localhost:8502
3. You'll see the **Today's Prices (Real-Time Stream)** section at the top
4. Prices update automatically every 5 seconds (cache TTL)

## Architecture

```
┌─────────────────────────────────────────────────────┐
│         stream_prices.py (Background)              │
│  • Fetches 1-min candles every 60 seconds         │
│  • Writes to data/cache/intraday_prices.json      │
└─────────────────────────────────────────────────────┘
                          ↓
                    JSON Cache File
                          ↓
┌─────────────────────────────────────────────────────┐
│    .streamlit/streamlit_app.py (Dashboard)        │
│  • Reads cache with 5s TTL refresh                │
│  • Displays latest prices at top                  │
│  • Shows "Waiting for stream..." if inactive      │
└─────────────────────────────────────────────────────┘
```

## Configuration

### Customize Update Interval

Edit `stream_prices.py` and change the `interval_seconds` parameter:

```python
if __name__ == "__main__":
    # Stream prices every 60 seconds (default)
    stream_prices(interval_seconds=60)
    
    # Or customize:
    stream_prices(interval_seconds=30)  # Update every 30 seconds
```

### Customize Max Duration

```python
if __name__ == "__main__":
    # Run for up to 90 hours
    stream_prices(max_duration_hours=90)
    
    # Or run indefinitely:
    stream_prices(max_duration_hours=float('inf'))
```

## Data Format

The cache file (`data/cache/intraday_prices.json`) has this structure:

```json
{
  "timestamp": "2026-04-07T12:30:45.123456+00:00",
  "date": "2026-04-07",
  "tickers": {
    "AAPL": [
      {
        "timestamp": "2026-04-07T09:35:00",
        "open": 186.50,
        "high": 187.25,
        "low": 186.40,
        "close": 187.15,
        "volume": 1245000
      },
      ...more candles...
    ],
    "TSLA": [...],
    "MSFT": [...]
  }
}
```

## Troubleshooting

### "Real-time price stream not active"

- Check if `stream_prices.py` is running
- Verify `data/cache/intraday_prices.json` exists and is being updated
- Check console for errors

### Prices not updating

- Market may be closed (NYSE trading hours: 9:30 AM - 4:00 PM ET, weekdays)
- Check your internet connection
- Verify yfinance is working: `python -c "import yfinance as yf; print(yf.download('AAPL', period='1d'))"`

### No data for some tickers

- May indicate market hours issue
- Try running during NYSE trading hours
- Check individual ticker availability with yfinance

## Integration with Dashboard

The Streamlit app now:

1. **Reads from stream cache** - Automatically checks `data/cache/intraday_prices.json`
2. **Shows live prices** - Displays latest close price for each ticker
3. **Cache refresh** - Updates every 5 seconds
4. **Fallback behavior** - Shows "Waiting for stream..." if no data available

Price accuracy depends on:
- Market hours (real prices only during NYSE hours)
- Internet connectivity
- yfinance availability

## Running Multiple Instances

You can run multiple instances if needed:

```bash
# Terminal 1: Main stream
python stream_prices.py

# Terminal 2 (optional): Dashboard still works independently
# (Already running at http://localhost:8502)
```

## Stopping the Stream

In the terminal where `stream_prices.py` is running, press:
```
Ctrl + C
```

The dashboard will show "Waiting for stream..." and continue to work with cache data until the cache is too old.
