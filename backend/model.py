import pandas as pd
import numpy as np
import xgboost as xgb
import shap
import json
import statsmodels.api as sm

def analyze_revenue_drivers(csv_path, anomaly_date):
    df = pd.read_csv(csv_path)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').set_index('date')
    
    target_kpi = 'total_revenue'
    feature_cols = [
        'total_cogs', 'total_orders', 'total_returns', 'total_sessions', 
        'total_pageviews', 'daily_ad_spend', 'daily_new_leads', 
        'gross_margin_pct', 'conversion_rate', 'cac', 'return_rate'
    ]
    
    ts_model = sm.tsa.UnobservedComponents(df[target_kpi], level='local linear trend')
    ts_results = ts_model.fit(disp=False)
    
    counterfactual = ts_results.predict(start=anomaly_date, end=anomaly_date)[0]
    actual_value = df.loc[anomaly_date, target_kpi]
    variance = actual_value - counterfactual
    
    X = df[feature_cols]
    y = df[target_kpi]
    
    xgb_model = xgb.XGBRegressor(objective='reg:squarederror', n_estimators=100, random_state=42)
    xgb_model.fit(X, y)
    
    explainer = shap.TreeExplainer(xgb_model)
    shap_values = explainer.shap_values(X)
    
    anomaly_idx = df.index.get_loc(pd.to_datetime(anomaly_date))
    anomaly_shap = shap_values[anomaly_idx]
    
    drivers = []
    for i, col in enumerate(feature_cols):
        drivers.append({
            "feature_name": col,
            "contribution_weight": round(float(anomaly_shap[i]), 4),
            "feature_value": round(float(X.iloc[anomaly_idx, i]), 4)
        })
        
    drivers.sort(key=lambda x: abs(x["contribution_weight"]), reverse=True)
    
    output = {
        "target_kpi": target_kpi,
        "anomaly_date": anomaly_date,
        "actual_revenue": round(float(actual_value), 4),
        "baseline_revenue": round(float(counterfactual), 4),
        "variance_magnitude": round(float(variance), 4),
        "ranked_drivers": drivers,
        "model_metrics": {
            "r2_score": round(float(xgb_model.score(X, y)), 4)
        }
    }
    
    return json.dumps(output, indent=4)
