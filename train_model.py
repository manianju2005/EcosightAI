import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.metrics import accuracy_score, classification_report
import joblib

# ================================
# 1. Load Dataset
# ================================
df = pd.read_csv("iot_extreme_dataset.csv")

X = df.drop("label", axis=1)
y = df["label"]

# ================================
# 2. Train-Test Split
# ================================
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# ================================
# 3. Feature Scaling (for LR & IF)
# ================================
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Save scaler
joblib.dump(scaler, "scaler.pkl")

# ================================
# 4. Logistic Regression (Baseline)
# ================================
lr_model = LogisticRegression(max_iter=1000)
lr_model.fit(X_train_scaled, y_train)

y_pred_lr = lr_model.predict(X_test_scaled)

print("\n=== Logistic Regression Results ===")
print("Accuracy:", accuracy_score(y_test, y_pred_lr))
print(classification_report(y_test, y_pred_lr))

joblib.dump(lr_model, "logistic_model.pkl")

# ================================
# 5. Random Forest (Main Model)
# ================================
rf_model = RandomForestClassifier(
    n_estimators=150,
    max_depth=10,
    random_state=42
)

rf_model.fit(X_train, y_train)

y_pred_rf = rf_model.predict(X_test)

print("\n=== Random Forest Results ===")
print("Accuracy:", accuracy_score(y_test, y_pred_rf))
print(classification_report(y_test, y_pred_rf))

joblib.dump(rf_model, "random_forest_model.pkl")

# ================================
# 6. Isolation Forest (Dynamic Baseline)
# ================================
iso_model = IsolationForest(
    n_estimators=100,
    contamination=0.1,
    random_state=42
)

iso_model.fit(X_train_scaled)

iso_preds = iso_model.predict(X_test_scaled)
iso_preds = np.where(iso_preds == -1, 1, 0)  # Convert to anomaly labels

print("\n=== Isolation Forest Results ===")
print("Accuracy:", accuracy_score(y_test, iso_preds))
print(classification_report(y_test, iso_preds))

joblib.dump(iso_model, "isolation_forest_model.pkl")

print("\nAll models trained and saved successfully!")
