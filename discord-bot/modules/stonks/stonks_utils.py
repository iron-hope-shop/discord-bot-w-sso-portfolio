import matplotlib.pyplot as plt
from io import BytesIO
import numpy as np
import pandas as pd

def calculate_rsi(prices, window=14):
    delta = np.diff(prices)
    gain = (delta > 0) * delta
    loss = (delta < 0) * -delta
    avg_gain = np.convolve(gain, np.ones((window,)) / window, mode="valid")
    avg_loss = np.convolve(loss, np.ones((window,)) / window, mode="valid")
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return np.concatenate((np.full(window - 1, np.nan), rsi))

def create_stock_chart(time, stock_prices):
    plt.figure(figsize=(10, 5))
    plt.plot(time, stock_prices, label="Stock Price", color="green", linewidth=2)
    plt.xlabel("Time", fontsize=12)
    plt.ylabel("Price", fontsize=12)
    plt.title("Simulated Stock Prices", fontsize=16)
    plt.legend()
    plt.grid(True)

    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close()
    return buf

def create_rsi_chart(time, rsi):
    plt.figure(figsize=(10, 5))
    valid_time = time[-len(rsi) :]  # Match the length of time with rsi
    plt.plot(valid_time, rsi, label="RSI", color="blue", linewidth=2)
    plt.axhline(y=70, color="red", linestyle="--", label="Overbought")
    plt.axhline(y=30, color="red", linestyle="--", label="Oversold")
    plt.xlabel("Time", fontsize=12)
    plt.ylabel("RSI", fontsize=12)
    plt.title("Relative Strength Index (RSI)", fontsize=16)
    plt.legend()
    plt.grid(True)

    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close()
    return buf

def create_stats_table(stock_prices, rsi):
    current_price = stock_prices[-1]
    highest_price = np.max(stock_prices)
    lowest_price = np.min(stock_prices)
    current_rsi = rsi[-1]

    data = {
        "Metric": ["Current Price", "Highest Price", "Lowest Price", "Current RSI"],
        "Value": [
            f"${current_price:.2f}",
            f"${highest_price:.2f}",
            f"${lowest_price:.2f}",
            f"{current_rsi:.2f}",
        ],
    }
    df = pd.DataFrame(data)
    return df

def generate_simulated_data():
    np.random.seed(42)
    time = np.arange(0, 50)  # Smaller interval
    stock_prices = 100 + np.cumsum(np.random.normal(0, 1, 50))
    return time, stock_prices