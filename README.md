# 🚀 BlockMind – The Intelligent CryptoBrain for Every User

BlockMind is a full-stack, AI-driven Personalized Crypto Portfolio Assets Performance Tracker Power BI analytics solution that helps users to track, analyze, and predict the performance of their cryptocurrency portfolio using real-time data, market sentiment, and technical indicators.

Live Demo: [Power BI Dashboard](https://app.powerbi.com/reportEmbed?reportId=03638c29-a144-432d-950f-f744009dcfcd&autoAuth=true&ctid=5eafb13a-8bcd-462a-9e16-58810b6f2460)

🧠 _"It's not just data — it's insight, redefined."_

---

## 📌 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Features](#features)
- [Power BI Dashboard](#power-bi-dashboard)
- [Power Apps Integration](#power-apps-integration)
- [Power Automate Flows](#power-automate-flows)
- [Flask API (Backend)](#flask-api-backend)
- [Data Sources (M Query)](#data-sources-m-query)
- [DAX Measures](#dax-measures)
- [Deployment Guide](#deployment-guide)
- [Screenshots](#screenshots)

---

Here’s a **fixed, polished version** of your **Overview** section with improved readability, flow, and professional tone:

---

## 📖 Overview

**BlockMind** enables users to:

* Register crypto assets through Power Apps (coin name, symbol, purchase date), which are sent via Power Automate to the Flask API and stored in MongoDB. *(Free for the first coin; ₹49 per additional coin)*
* Collect real-time data such as coin information, market charts, and OHLC (hourly & yearly) from the CoinGecko API, along with news and Reddit sentiment data, and store it in MongoDB.
* Perform advanced analysis in the Flask backend using Python libraries like **Pandas, NumPy, TextBlob, and TA-Lib**, then save the processed insights back into MongoDB.
* Expose all data and insights via Flask API endpoints, which are seamlessly connected to Power BI for interactive dashboards.
* Track portfolio returns, profit/loss, and performance metrics with dynamic KPIs.
* Analyze crypto market sentiment from **news** and **Reddit** data.
* Receive automated **daily alerts via a Telegram bot**.

All insights are personalized based on each user’s portfolio and powered by the Flask API + MongoDB backend.

---

## 🏗️ Architecture

flowchart LR
    A[📱 Power Apps] --> B[⚡ Power Automate]
    B --> C[🌐 Flask API (Render)]
    C --> D[📊 Data Sources: CoinGecko, News API, Reddit]
    D --> E[🗄️ MongoDB Atlas]
    E --> F[🌐 Flask API (Render)]
    F --> G[📈 Power BI Desktop]
    F --> H[🤖 Telegram Bot (Daily Alerts)]
    G --> I[📊 Power BI Service (Dashboard)]

---

## 🛠 Tech Stack

| Layer            | Tech Used                      |
|------------------|--------------------------------|
| Frontend UI      | Power BI + Power Apps          |
| Backend API      | Flask (Python)                 |
| Database         | MongoDB Atlas                  |
| Automation       | Power Automate                 |
| Hosting          | Render.com                     |
| Data Sources     | CoinGecko API, News API, Reddit API |

---

## ✨ Features

- 🪙 Real-time coin tracking with dynamic KPIs
- 📉 Price change analysis over 1H, 24H, 7D, 30D, 1Y
- 🔮 Bollinger Bands, RSI, MACD, Volatility insights
- 📊 Personalized ₹10K investment simulation
- 🧠 AI-generated buy/sell/hold insights
- 📈 Candlestick charts with SMA/EMA trendlines
- 📰 Sentiment score from news and Reddit
- 🔁 Hourly + yearly market & candlestick data

---

## 📊 Power BI Dashboard

Contains:
- **Overview Page:** Top performing coins, ROI %, profit/loss metrics
- **Trend Analysis:** Bollinger Bands, Moving Averages, AI insights
- **Sentiment Analysis:** Reddit + News scorecards
- **Drill-through Pages:** Coin-wise deep dive
- **KPIs** like:
  - `[14D Price Change %]`
  - `[₹10K Investment Insight]`
  - `[Volatility Insight]`
  - `[SMA 200 Insight]`
  - `[Investment Decision Insight]`

---

## 📱 Power Apps Integration

### 1. **Register New User**
- Collects: `Coin Name`, `Symbol`, `Purchase Date`
- Sends data to MongoDB via API

### 2. **Asset Tracker**
- Retrieves all user coins and metrics from MongoDB
- Displayed in Power BI embedded app

### 3. **API Trigger / Refresh**
- Calls Power Automate flow to refresh live insights

Power Apps are embedded directly into Power BI dashboard pages.

---

## 🔄 Power Automate Flows

Used to:
- Trigger Flask API calls
- Send user-input data from Power Apps
- Receive responses to confirm asset creation or refresh

✅ All flows are **instant flows** connected to **Power App button**.

---

## 🌐 Flask API (Backend)

Hosted on: `https://cryptodata-pnzi.onrender.com`

### Key Endpoints:
| Endpoint                              | Description                            |
|---------------------------------------|----------------------------------------|
| `/get-analyzed-data`                 | Returns portfolio + live metrics       |
| `/get-hourly-candlestick-data`       | OHLC data for hourly trendlines        |
| `/get-yearly-candlestick-data`       | 1-year candlestick prices              |
| `/get-hourly-market-chart-data`      | Hourly price line chart                |
| `/get-yearly-market-chart-data`      | 1Y growth line chart                   |
| `/get-news-data`                     | Sentiment & price impact of news       |

MongoDB stores user assets and analyzed coin data.

---

## 🔍 Data Sources (M Query)

**Power Query Editor** fetches from Flask endpoints:

- ✅ `User Portfolio`
- ✅ `Hourly & Yearly Candlestick Data`
- ✅ `News + Sentiment`
- ✅ `Market Charts`

Custom transformations done using:
- `Table.ExpandRecordColumn`
- `Table.AddColumn` with dynamic lookup
- Type casting and renaming

See: [`Data Source.txt`](./Data%20Source.txt)

---

## 📐 DAX Measures

Over 20+ dynamic measures:

- Price % change over multiple timeframes
- Moving averages (SMA_200, EMA_20)
- Volatility and CAGR insights
- Buy/Sell recommendations based on market + volatility
- Custom UI HTML (animated welcome banner)

See: [`Generated DAX Query.txt`](./Generated%20DAX%20Query.txt)

---

## 🚀 Deployment Guide

1. **Flask App**
   - Deploy to Render using Gunicorn and `requirements.txt`
   - Add your MongoDB connection string as environment variable

2. **MongoDB**
   - Free cluster on MongoDB Atlas
   - Collection: `user_assets`, `coin_analysis`

3. **Power BI**
   - Load all data via Web.Contents (M query)
   - Use DAX to define KPIs and logic

4. **Power Apps**
   - Create 3 screens
   - Use `Patch` or `Flow` to send data to Automate

5. **Power Automate**
   - Create flow → HTTP request → Send to Flask → Return response

---

## 🖼 Screenshots

### Dashboard Preview  
![Dashboard](./BlockMind.pdf)

### Trend Analysis  
- Candlestick with SMA/Bollinger
- Volatility heatmap

### Sentiment Report  
- News & Reddit posts
- AI-generated score

---

## 📎 Links

- 🧠 [Live Netlify Portfolio](https://ankit-sharma-07.netlify.app)
- 📂 [Flask Backend Source (ZIP)](./BlockMind.zip)
- 🧾 [Full DAX Measures](./Generated%20DAX%20Query.txt)
- 🔗 [Power BI PDF Report](./BlockMind.pdf)

---

## 🙌 Credits

**Developer:** [Ankit Sharma](https://ankit-sharma-07.netlify.app)  
Built as a personal portfolio + resume booster for **Data Analyst** roles.

---


