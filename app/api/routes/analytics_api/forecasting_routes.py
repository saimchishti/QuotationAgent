# app/api/routes/forecasting_routes.py

from fastapi import APIRouter, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_
from prophet import Prophet
import pandas as pd
import requests
from datetime import timedelta, date
import holidays

from db.models import WeatherCache, BusinessOwnerCase1
from db.session import get_db
from services.dataprovider import get_training_data

router = APIRouter()
FORECAST_API_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_API_URL  = "https://archive-api.open-meteo.com/v1/archive"

@router.get("/forecast", tags=["Sales Forecast"])
async def forecast_sales(
    business_owner_id: int = Query(..., description="Business owner ID to filter data"),
    session: AsyncSession = Depends(get_db)
):
    # 1) Fetch business owner coordinates
    owner_res = await session.execute(
        select(BusinessOwnerCase1).where(BusinessOwnerCase1.id == business_owner_id)
    )
    owner = owner_res.scalars().first()
    if not owner or owner.lat is None or owner.lon is None:
        return {"error": "Business owner coordinates not found"}

    LATITUDE  = float(owner.lat)
    LONGITUDE = float(owner.lon)

    # 2) Load training data (includes past weather)
    df = await get_training_data(business_owner_id)
    if df.empty or len(df) < 2:
        return {"error": "Not enough data to train the model"}

    # 3) Prepare daily-aggregated series for Prophet
    df["ds"] = pd.to_datetime(df["datetime"]).dt.tz_localize(None)
    daily_df = (
        df.groupby("ds")
          .agg(
            y             = ("quantity", "sum"),
            temp_max      = ("temp_max", "mean"),
            temp_min      = ("temp_min", "mean"),
            precipitation = ("precipitation", "mean"),
            weather_code  = ("weather_code", "mean"),
          )
          .reset_index()
    )

    # 3a) Add weekend and holiday flags
    pk_holidays = holidays.country_holidays("PK")
    daily_df["holiday_flag"] = daily_df["ds"].dt.date.isin(pk_holidays).astype(int)
    daily_df["weekend_flag"] = daily_df["ds"].dt.weekday.isin([5,6]).astype(int)

    # forward/backfill regressors
    for col in ["temp_max", "temp_min", "precipitation", "weather_code"]:
        daily_df[col] = daily_df[col].ffill().bfill()

    # 4) Fit Prophet model with regressors
    model = Prophet(daily_seasonality=True, weekly_seasonality=True, yearly_seasonality=True)
    for col in ["temp_max", "temp_min", "precipitation", "weather_code", "holiday_flag", "weekend_flag"]:
        model.add_regressor(col)
    model.fit(daily_df)

    # 5) Build 7-day forecast window
    last_date = daily_df["ds"].max().normalize()
    today     = pd.Timestamp(date.today())
    if last_date > today:
        last_date = today

    forecast_dates = pd.date_range(
        start=last_date + timedelta(days=1),
        periods=7,
        freq="D"
    )
    past_dates   = [d.date() for d in forecast_dates if d <= today]
    future_dates = [d.date() for d in forecast_dates if d >  today]

    # 6) Gather weather data (cache → archive or forecast API)
    weather_records = []

    # 6a) Past (archive) dates
    if past_dates:
        stmt = select(WeatherCache).where(
            and_(
                WeatherCache.date.in_(past_dates),
                WeatherCache.latitude  == LATITUDE,
                WeatherCache.longitude == LONGITUDE
            )
        )
        cached = (await session.execute(stmt)).scalars().all()
        cached_dates = {r.date for r in cached}
        weather_records.extend(cached)

        missing = set(past_dates) - cached_dates
        if missing:
            params = {
                "latitude": LATITUDE,
                "longitude": LONGITUDE,
                "start_date": min(missing).strftime("%Y-%m-%d"),
                "end_date":   max(missing).strftime("%Y-%m-%d"),
                "daily":      "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode",
                "timezone":   "Asia/Karachi"
            }
            resp = requests.get(ARCHIVE_API_URL, params=params)
            if resp.status_code != 200:
                return {"error": "Failed to fetch historical weather"}
            df_arc = pd.DataFrame(resp.json()["daily"])
            df_arc["ds"] = pd.to_datetime(df_arc["time"])
            for _, row in df_arc.iterrows():
                ent = WeatherCache(
                    date          = row["ds"].date(),
                    latitude      = LATITUDE,
                    longitude     = LONGITUDE,
                    temp_max      = row["temperature_2m_max"],
                    temp_min      = row["temperature_2m_min"],
                    precipitation = row["precipitation_sum"],
                    weather_code  = row["weathercode"],
                )
                session.add(ent)
                weather_records.append(ent)
            await session.commit()

    # 6b) Future (forecast) dates
    if future_dates:
        stmt = select(WeatherCache).where(
            and_(
                WeatherCache.date.in_(future_dates),
                WeatherCache.latitude  == LATITUDE,
                WeatherCache.longitude == LONGITUDE
            )
        )
        cached = (await session.execute(stmt)).scalars().all()
        cached_dates = {r.date for r in cached}
        weather_records.extend(cached)

        missing = set(future_dates) - cached_dates
        if missing:
            params = {
                "latitude": LATITUDE,
                "longitude": LONGITUDE,
                "start_date": min(missing).strftime("%Y-%m-%d"),
                "end_date":   max(missing).strftime("%Y-%m-%d"),
                "daily":      "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode",
                "timezone":   "Asia/Karachi"
            }
            resp = requests.get(FORECAST_API_URL, params=params)
            if resp.status_code != 200:
                return {"error": "Failed to fetch weather forecast"}
            df_fut = pd.DataFrame(resp.json()["daily"])
            df_fut["ds"] = pd.to_datetime(df_fut["time"])
            for _, row in df_fut.iterrows():
                ent = WeatherCache(
                    date          = row["ds"].date(),
                    latitude      = LATITUDE,
                    longitude     = LONGITUDE,
                    temp_max      = row["temperature_2m_max"],
                    temp_min      = row["temperature_2m_min"],
                    precipitation = row["precipitation_sum"],
                    weather_code  = row["weathercode"],
                )
                session.add(ent)
                weather_records.append(ent)
            await session.commit()

    # 7) Build forecast_weather_df
    weather_records.sort(key=lambda r: r.date)
    forecast_weather_df = pd.DataFrame([{
        "ds":           pd.to_datetime(r.date),
        "temp_max":     float(r.temp_max),
        "temp_min":     float(r.temp_min),
        "precipitation": float(r.precipitation),
        "weather_code":  int(r.weather_code)
    } for r in weather_records])

    # 8) Add holiday & weekend flags to forecast_weather_df
    forecast_weather_df["holiday_flag"] = forecast_weather_df["ds"].dt.date.isin(pk_holidays).astype(int)
    forecast_weather_df["weekend_flag"] = forecast_weather_df["ds"].dt.weekday.isin([5,6]).astype(int)

    # 9) Generate future dataframe & merge all regressors
    future = model.make_future_dataframe(periods=7, freq="D")
    future = future.merge(
        forecast_weather_df[
            ["ds", "temp_max", "temp_min", "precipitation", "weather_code", "holiday_flag", "weekend_flag"]
        ],
        on="ds", how="left"
    )
    future = future.merge(
        daily_df[
            ["ds", "temp_max", "temp_min", "precipitation", "weather_code", "holiday_flag", "weekend_flag"]
        ],
        on="ds", how="left", suffixes=("", "_hist")
    )
    for col in ["temp_max", "temp_min", "precipitation", "weather_code", "holiday_flag", "weekend_flag"]:
        future[col] = future[col].combine_first(future[f"{col}_hist"]).ffill().bfill()
        future.drop(columns=f"{col}_hist", inplace=True)

    # 10) Forecast & format results
    forecast   = model.predict(future)
    avg_sales  = daily_df["y"].mean()
    avg_price  = (df["price"].sum() / df["quantity"].sum()) if df["quantity"].sum() > 0 else 450

    def confidence_level(lo, hi, avg):
        spread = hi - lo
        if avg == 0:
            return "Low"
        ratio = spread / avg
        if ratio > 1.0:
            return "Low"
        elif ratio > 0.5:
            return "Medium"
        else:
            return "High"

    window  = forecast[forecast["ds"] >= last_date + timedelta(days=1)]
    results = [{
        "date":                  row["ds"].date().isoformat(),
        "forecast_amount":       int(row["yhat"]),
        "forecast_sales_amount": int(row["yhat"] * avg_price),
        "confidence_level":      confidence_level(row["yhat_lower"], row["yhat_upper"], avg_sales),
        "percentage_vs_avg":     f"{((row['yhat'] - avg_sales) / avg_sales * 100):+.0f}%"
    } for _, row in window.iterrows()]

    return {"forecast": results}


@router.get("/predict-traffic", tags=["Sales Forecast"])
async def predict_traffic_level(business_owner_id: int = Query(..., description="Business owner ID to filter data")):
    df = await get_training_data(business_owner_id)
    df['ds'] = pd.to_datetime(df['datetime']).dt.tz_localize(None)

    # Aggregate quantity per day
    df = df.groupby('ds').agg({'quantity': 'sum'}).reset_index().rename(columns={'quantity': 'y'})
    df = df.sort_values('ds')

    if len(df) < 2:
        return {"error": "Not enough data for forecasting"}

    avg_sales = df['y'].mean()

    # Fit Prophet
    model = Prophet(daily_seasonality=True, weekly_seasonality=True)
    model.fit(df)

    # Forecast next 7 days
    future = model.make_future_dataframe(periods=7, freq='D')
    forecast = model.predict(future)
    forecast_next_7 = forecast[forecast['ds'] > df['ds'].max()][['ds', 'yhat', 'yhat_lower', 'yhat_upper']].copy()

    output = []
    for _, row in forecast_next_7.iterrows():
        expected_sales = row['yhat']

        # Compare with average sales to determine traffic level
        if expected_sales >= avg_sales * 1.15:
            traffic = "High"
        elif expected_sales >= avg_sales * 0.85:
            traffic = "Medium"
        else:
            traffic = "Low"

        output.append({
            "date": row['ds'].date().isoformat(),
            "expected_sales": int(expected_sales),
            "traffic_level": traffic
        })

    return output


@router.get("/contribution-breakdown", tags=["Sales Forecast"])
async def contribution_breakdown(business_owner_id: int = Query(..., description="Business owner ID to filter data")):
    df = await get_training_data(business_owner_id)

    df['ds'] = pd.to_datetime(df['datetime']).dt.tz_localize(None)
    df = df.groupby('ds').agg({'quantity': 'sum'}).reset_index().rename(columns={'quantity': 'y'})
    df = df.sort_values('ds')

    model = Prophet(daily_seasonality=True, weekly_seasonality=True)
    model.fit(df)

    future = model.make_future_dataframe(periods=7, freq='D')
    forecast = model.predict(future)
    forecast_next_7 = forecast[forecast['ds'] > df['ds'].max()][['ds', 'yhat']].copy()

    pk_holidays = holidays.country_holidays('PK')
    breakdown_data = []

    total_yhat = forecast_next_7['yhat'].sum()
    total_holiday = 0
    total_weather = 0
    total_local_events = 0

    for _, row in forecast_next_7.iterrows():
        date = row['ds'].date()
        yhat = int(row['yhat'])

        holiday_effect = int(yhat * 0.08) if date in pk_holidays else 0
        weather = int(yhat * 0.15)
        local_events = int(yhat * 0.12)
        historical_trends = yhat - weather - local_events - holiday_effect

        total_holiday += holiday_effect
        total_weather += weather
        total_local_events += local_events

        breakdown_data.append({
            "date": date.isoformat(),
            "historical_trends": historical_trends,
            "weather": weather,
            "local_events": local_events,
            "holiday_effect": holiday_effect
        })

    total_historical = total_yhat - total_holiday - total_weather - total_local_events

    contributions = {
        "historical_trends": {
            "percentage": round(total_historical / total_yhat * 100),
            "description": "Primary driver"
        },
        "weather": {
            "percentage": round(total_weather / total_yhat * 100),
            "description": "Seasonal impact"
        },
        "local_events": {
            "percentage": round(total_local_events / total_yhat * 100),
            "description": "Event-driven boost"
        },
        "holiday_effect": {
            "percentage": round(total_holiday / total_yhat * 100),
            "description": "Special occasions"
        }
    }

    return {
        "data": breakdown_data,
        "contributions": contributions
    }


@router.get("/order-type-forecast", tags=["Sales Forecast"])
async def forecast_order_type_mix(business_owner_id: int = Query(..., description="Business owner ID to filter data")):
    df = await get_training_data(business_owner_id)

    df['ds'] = pd.to_datetime(df['datetime']).dt.tz_localize(None)
    df = df.sort_values('ds')

    if 'order_type_id' not in df.columns:
        return {"error": "Missing order_type_id in training data."}

    results = {}
    last_date = df['ds'].max()
    future_dates = None

    for order_type_id, label in [(1, 'takeaway'), (2, 'dine_in'), (3, 'delivery')]:
        df_type = df[df['order_type_id'] == order_type_id]
        df_type = df_type.groupby('ds').agg({'quantity': 'sum'}).reset_index().rename(columns={'quantity': 'y'})
        if df_type.empty:
            continue

        model = Prophet(daily_seasonality=True, weekly_seasonality=True)
        model.fit(df_type)

        future = model.make_future_dataframe(periods=7, freq='D')
        forecast = model.predict(future)
        forecast_7 = forecast[forecast['ds'] > last_date][['ds', 'yhat']].copy()
        forecast_7['yhat'] = forecast_7['yhat'].clip(lower=0).round().astype(int)

        if future_dates is None:
            future_dates = forecast_7[['ds']].copy()
            future_dates['date'] = future_dates['ds'].dt.date.astype(str)

        results[label] = forecast_7['yhat'].values

    response = []
    for i in range(len(future_dates)):
        response.append({
            "date": future_dates.iloc[i]['date'],
            "dine_in": int(results.get('dine_in', [0]*7)[i]),
            "delivery": int(results.get('delivery', [0]*7)[i]),
            "takeaway": int(results.get('takeaway', [0]*7)[i])
        })

    return response
@router.get("/top-dishes-forecast", tags=["Sales Forecast"])
async def top_dishes_forecast(limit: int = 5 ,business_owner_id: int = Query(..., description="Business owner ID to filter data")):
    df = await get_training_data(business_owner_id)

    df['ds'] = pd.to_datetime(df['delivery_datetime']).dt.tz_localize(None)

    if df.empty or 'menu_name' not in df.columns:
        return {"error": "No sufficient data for forecasting."}

    df = df.sort_values('ds')

    last_date = df['ds'].max()
    start_of_last_week = last_date - pd.Timedelta(days=6)

    # Top dishes of last 7 days
    last_week_df = df[(df['ds'] >= start_of_last_week) & (df['ds'] <= last_date)]
    recent_top = (
        last_week_df.groupby('menu_name')['quantity']
        .sum()
        .sort_values(ascending=False)
        .head(limit)
        .reset_index()
        .rename(columns={'quantity': 'last_week_sales'})
    )

    # Forecast next 7 days for each dish
    forecast_results = []

    for dish in df['menu_name'].unique():
        dish_df = df[df['menu_name'] == dish][['ds', 'quantity']].copy()
        if len(dish_df) < 2:
            continue  # Not enough data

        dish_df.rename(columns={'quantity': 'y'}, inplace=True)

        try:
            model = Prophet(daily_seasonality=True, weekly_seasonality=True)
            model.fit(dish_df)
            future = model.make_future_dataframe(periods=7, freq='D')
            forecast = model.predict(future)
            next_7 = forecast[forecast['ds'] > last_date]
            total_forecast = int(next_7['yhat'].clip(lower=0).sum())
            forecast_results.append({"menu_name": dish, "forecast_quantity": total_forecast})
        except Exception as e:
            print(f"⚠️ Could not forecast for dish: {dish} → {str(e)}")
            continue

    forecast_df = pd.DataFrame(forecast_results)
    top_forecast = forecast_df.sort_values(by='forecast_quantity', ascending=False).head(limit)

    return {
        "top_dishes_last_week": recent_top.to_dict(orient="records"),
        "top_dishes_next_week_forecast": top_forecast.to_dict(orient="records")
    }

@router.get("/time-distribution", tags=["Sales Forecast"])
async def time_distribution(business_owner_id: int = Query(..., description="Business owner ID to filter data")):
    df = await get_training_data(business_owner_id)


    if df.empty or 'time_of_day_category' not in df.columns:
        return {"error": "Insufficient data or missing time category."}

    df['ds'] = pd.to_datetime(df['delivery_datetime']).dt.tz_localize(None)
    df['weekday'] = df['ds'].dt.day_name()

    # Step 1: Historical Aggregation
    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    time_order = ["Breakfast", "Lunch", "Evening", "Dinner"]

    historical_agg = (
        df.groupby(['weekday', 'time_of_day_category'])['quantity']
        .sum()
        .reset_index()
    )

    pivot = historical_agg.pivot(index='weekday', columns='time_of_day_category', values='quantity').fillna(0)
    pivot = pivot.reindex(weekday_order).fillna(0)

    # Calculate time-of-day distribution ratios per weekday
    ratios = pivot.div(pivot.sum(axis=1), axis=0).fillna(0)

    # Step 2: Get forecasted daily sales
    df_prophet = df[['ds', 'quantity']].rename(columns={'ds': 'ds', 'quantity': 'y'})
    model = Prophet(daily_seasonality=True, weekly_seasonality=True)
    model.fit(df_prophet)

    future = model.make_future_dataframe(periods=7, freq='D')
    forecast = model.predict(future)
    last_date = df['ds'].max()
    forecast_7 = forecast[forecast['ds'] > last_date][['ds', 'yhat']].copy()
    forecast_7['weekday'] = forecast_7['ds'].dt.day_name()

    # Step 3: Distribute forecasted sales into time slots using historical ratios
    result = []
    for _, row in forecast_7.iterrows():
        day_name = row['weekday']
        daily_sales = row['yhat']
        row_data = {"weekday": day_name}
        for time_slot in time_order:
            portion = ratios.loc[day_name].get(time_slot, 0)
            row_data[time_slot] = int(daily_sales * portion)
        result.append(row_data)

    return {
        "forecast_distribution": result,
        "historical_distribution": pivot.astype(int).reset_index().to_dict(orient="records")
    }
@router.get("/forecast-accuracy-trend", tags=["Sales Forecast"])
async def forecast_accuracy_trend(business_owner_id: int = Query(..., description="Business owner ID to filter data")):
    df = await get_training_data(business_owner_id)

    df['ds'] = pd.to_datetime(df['delivery_datetime']).dt.tz_localize(None)
    df = df.sort_values('ds')

    # Prepare data for Prophet
    df_prophet = df[['ds', 'quantity']].rename(columns={'quantity': 'y'}).copy()

    # Define cutoff to exclude last 7 days
    max_date = df_prophet['ds'].max()
    cutoff_date = max_date - timedelta(days=7)

    train_df = df_prophet[df_prophet['ds'] < cutoff_date]
    test_df = df_prophet[df_prophet['ds'] >= cutoff_date]

    if len(train_df) < 14 or len(test_df) < 1:
        return {"error": "Not enough data to compute accuracy."}

    # Train model on data excluding last 7 days
    model = Prophet(daily_seasonality=True, weekly_seasonality=True)
    model.fit(train_df)

    # Forecast for the last 7 days
    future = test_df[['ds']].copy()
    forecast = model.predict(future)

    # Evaluate forecast accuracy
    accuracy_records = []
    for i in range(len(test_df)):
        y_true = test_df.iloc[i]['y']
        y_pred = forecast.iloc[i]['yhat']
        accuracy = max(0, min(1, 1 - abs(y_true - y_pred) / y_true)) if y_true != 0 else 0

        accuracy_records.append({
            "date": test_df.iloc[i]['ds'].date().isoformat(),
            "actual_sales": int(y_true),
            "predicted_sales": round(y_pred),
            "accuracy_percent": round(accuracy * 100, 1)
        })

    # Average accuracy
    average_accuracy = round(
        sum([r['accuracy_percent'] for r in accuracy_records]) / len(accuracy_records), 1
    )

    return {
        "average_accuracy": average_accuracy,
        "trend": accuracy_records,
        "status": "Model performance is good" if average_accuracy >= 85 else "Needs improvement"
    }
    
@router.get("/dashboard-summary", tags=["Sales Forecast"])
async def dashboard_summary(business_owner_id: int = Query(..., description="Business owner ID to filter data")):
    df = await get_training_data(business_owner_id)

    df['ds'] = pd.to_datetime(df['delivery_datetime']).dt.tz_localize(None)
    df = df.sort_values('ds')

    df_prophet = df[['ds', 'quantity', 'price']].copy()
    df_prophet = df_prophet.rename(columns={'quantity': 'y'})

    # Train Prophet
    model = Prophet(daily_seasonality=True, weekly_seasonality=True)
    model.fit(df_prophet[['ds', 'y']])

    future = model.make_future_dataframe(periods=7, freq='D')
    forecast = model.predict(future)
    forecast_next_7 = forecast[forecast['ds'] > df_prophet['ds'].max()][['ds', 'yhat', 'yhat_lower', 'yhat_upper']]

    # Orders forecast
    weekly_orders = int(forecast_next_7['yhat'].sum())

    # Revenue forecast (use avg price * forecast quantity)
    avg_price_per_unit = df['price'].sum() / df['quantity'].sum()
    revenue_forecast = int(weekly_orders * avg_price_per_unit)

    # Peak hours from historical
    df['hour'] = df['ds'].dt.hour
    hour_agg = df.groupby('hour')['quantity'].sum()
    peak_hour_range = hour_agg.idxmax()
    peak_hour_label = f"{peak_hour_range}:00 - {peak_hour_range+1}:00"

    # High alert days: low confidence = wide yhat range
    forecast_next_7['spread'] = forecast_next_7['yhat_upper'] - forecast_next_7['yhat_lower']
    alert_days = forecast_next_7[forecast_next_7['spread'] > 5000]
    high_alert_count = len(alert_days)

    return {
        "weekly_orders": weekly_orders,
        "revenue_forecast": revenue_forecast,
        "peak_hours": peak_hour_label,
        "high_alert_days": high_alert_count
    }
