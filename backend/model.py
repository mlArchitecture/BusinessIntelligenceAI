import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error
from sklearn.preprocessing import StandardScaler

# ============================================================
# LOAD DATA
# ============================================================

# df = pd.read_csv('final_data.csv') # Original line, caused error
df = testing_df # Use the already prepared final_df DataFrame

# ------------------------------------------------------------
# IMPORTANT: excluded from features —
#   gross_margin_pct : LEAKAGE — formula is (revenue - cogs) / revenue,
#                       revenue is literally inside it. Never use as a predictor.
# ------------------------------------------------------------

FEATURE_COLS = [
    'order_count', 'gross_margin_pct','conversion_rate', 'sessions', 'spend',
    'cac', 'return_rate', 'freshness_hours',
    
]
TARGET_COL = 'revenue'

# Drop rows with NaN in features/target (zero-activity days will have NaN
# ratio KPIs from the fixed pipeline — that's expected, not a bug)
model_df = df.dropna(subset=FEATURE_COLS + [TARGET_COL]).copy()
print(f"Using {len(model_df)} of {len(df)} rows after dropping NaN rows")

X = model_df[FEATURE_COLS]
y = model_df[TARGET_COL]


# ============================================================
# TRAIN / TEST SPLIT
# ============================================================
# If you have a 'date' column, use a TIME-based split instead — uncomment below
# and comment out the random split. This avoids leaking adjacent-day info
# between train and test, which a random split doesn't protect against.

# model_df = model_df.sort_values('date')
# split_idx = int(len(model_df) * 0.8)
# X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
# y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)


# ============================================================
# BASELINE MODEL: Linear Regression
# ============================================================
# Simple, interpretable — coefficients directly show direction + rough
# magnitude of each driver's effect. Good for the "deterministic, explainable"
# story your BI track cares about.

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

lin_model = LinearRegression()
lin_model.fit(X_train_scaled, y_train)

lin_preds = lin_model.predict(X_test_scaled)
print("\n--- Linear Regression ---")
print(f"R²:  {r2_score(y_test, lin_preds):.3f}")
print(f"MAE: {mean_absolute_error(y_test, lin_preds):.2f}")

lin_coefs = pd.DataFrame({
    'feature': FEATURE_COLS,
    'coefficient': lin_model.coef_
}).sort_values('coefficient', key=abs, ascending=False)
print("\nLinear model coefficients (standardized — comparable magnitude):")
print(lin_coefs)


# ============================================================
# MAIN MODEL: Random Forest (captures non-linear driver interactions)
# ============================================================

rf_model = RandomForestRegressor(
    n_estimators=200, max_depth=8, min_samples_leaf=5, random_state=42
)
rf_model.fit(X_train, y_train)

rf_preds = rf_model.predict(X_test)
print("\n--- Random Forest ---")
print(f"R²:  {r2_score(y_test, rf_preds):.3f}")
print(f"MAE: {mean_absolute_error(y_test, rf_preds):.2f}")

rf_importance = pd.DataFrame({
    'feature': FEATURE_COLS,
    'importance': rf_model.feature_importances_
}).sort_values('importance', ascending=False)
print("\nFeature importance (driver ranking for Day 4):")
print(rf_importance)


# ============================================================
# DRIVER RANKING OUTPUT — feeds directly into your Day 4 MovementEvent
# ============================================================

def rank_drivers(model, feature_cols, X_row):
    """
    Given a fitted model and a single row of features (e.g. the day of a
    detected movement), return ranked driver contributions.
    Uses simple permutation-style delta rather than full SHAP for speed —
    swap in shap.TreeExplainer if you have time budget for it.
    """
    baseline_pred = model.predict(X_row)[0]
    contributions = []
    for col in feature_cols:
        perturbed = X_row.copy()
        perturbed[col] = X[col].mean()   # replace with average value
        perturbed_pred = model.predict(perturbed)[0]
        contributions.append({
            'driver': col,
            'contribution': baseline_pred - perturbed_pred
        })
    ranked = pd.DataFrame(contributions).sort_values('contribution', key=abs, ascending=False)
    ranked['confidence'] = 'high' if r2_score(y_test, rf_preds) > 0.6 else 'medium'
    return ranked

# Example: explain drivers for one specific day
example_row = X.iloc[[0]]
print("\nExample driver ranking for one row:")
print(rank_drivers(rf_model, FEATURE_COLS, example_row))
