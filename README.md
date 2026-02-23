# Undervalued Home Discovery Engine

An AI-driven engine to identify significantly undervalued homes based on hyper-local property data, time-series trends, and aggressive machine learning models.

## Features
- **Real-World API**: Integrated with the **RentCast API** for live Tampa listings.
- **Financial Modeling**: Automatically calculates the capitalized impact of HOA fees on home-buying power.
- **Local Clustering**: Groups properties by geographic proximity or zip code.
- **Time-Series Correction**: Adjusts historical prices for market appreciation using synthetic market context.
- **Aggressive Overfitting**: Uses Perceptron Neural Networks to capture local pricing nuances.

## Installation
```bash
pip install -r requirements.txt
```

## Usage
1. **API Setup**: (Optional) Get a free key from [RentCast](https://rentcast.io/api) and add it to `config.py`.
2. **Train Context**: Generate historical data to give the engine "market memory".
   ```bash
   python3 data/generator.py
   ```
3. **Run Discovery**: Train models and find undervalued properties in the real world.
   ```bash
   python3 main.py
   ```

## Project Structure
- `data/`: Contains the data generator and manual/cached real-world datasets.
- `engine/`:
    - `api_client.py`: Client for fetching live real estate data.
    - `models.py`: ML model implementations.
    - `discovery_engine.py`: Core logic for pipeline execution.
- `config.py`: Configuration for API keys and financial constants.
- `main.py`: Entry point for the application.
