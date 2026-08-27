import pandas as pd
import numpy as np
import xgboost as xgb
import shap
import json
import statsmodels.api as sm

def analyze_forecast_variance(csv_path, today_date):
    df = pd.read_csv(csv_path)
    df['date'] = pd.to_datetime(df['date'])
    # df = df.sort_values('date').set_index('date') No need to sort based on date, assuming the data is already sorted based on date
    
    target_kpi = 'total_revenue'
    # Removed 'gross_margin_pct' and 'total_cogs' to prevent mathematical data leakage
    feature_cols = [
        'total_orders', 'total_returns', 'total_sessions', 
        'total_pageviews', 'daily_ad_spend', 'daily_new_leads', 
        'conversion_rate', 'cac', 'return_rate'
    ]
    
    today_dt = pd.to_datetime(today_date)
    
    # 1. Strict Temporal Boundary: Split history from the new data
    historical_df = df[df.index < today_dt]
    today_df = df[df.index == today_dt]
    
    if today_df.empty:
        return json.dumps({"error": f"Actual data for {today_date} has not been ingested yet."})
    
    # 2. Forecasting (Out-of-Sample Prediction)
    ts_model = sm.tsa.UnobservedComponents(historical_df[target_kpi], level='local linear trend')
    ts_results = ts_model.fit(disp=False)
    
    # Predict exactly 1 step into the future
    forecasted_value = ts_results.forecast(steps=1).iloc[0]
    actual_value = today_df[target_kpi].iloc[0]
    variance = actual_value - forecasted_value
    
    # 3. Train Driver Engine on Historical Data
    X_train = historical_df[feature_cols]
    y_train = historical_df[target_kpi]
    X_today = today_df[feature_cols]
    
    xgb_model = xgb.XGBRegressor(objective='reg:squarederror', n_estimators=100, random_state=42)
    xgb_model.fit(X_train, y_train)
    
    # 4. Extract Driverdata
   s strictly for the new variance
    explainer = shap.TreeExplainer(xgb_model)
    shap_values = explainer.shap_values(X_today)
    
    today_shap = shap_values[0] # Isolates the SHAP array for 'today'
    
    drivers = []
    for i, col in enumerate(feature_cols):
        drivers.append({
            "feature_name": col,
            "contribution_weight": round(float(today_shap[i]), 4),
            "feature_value": round(float(X_today.iloc[0, i]), 4)
        })
        
    drivers.sort(key=lambda x: abs(x["contribution_weight"]), reverse=True)
    
    output = {
        "target_kpi": target_kpi,
        "analysis_date": today_date,
        "actual_revenue": round(float(actual_value), 4),
        "forecasted_revenue": round(float(forecasted_value), 4),
        "variance_magnitude": round(float(variance), 4),
        "ranked_drivers": drivers,
        "model_metrics": {
            "historical_r2_score": round(float(xgb_model.score(X_train, y_train)), 4)
        }
    }
    
    return json.dumps(output, indent=4)
