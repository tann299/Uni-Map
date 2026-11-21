"""Minimal training pipeline for Uni Connect thesis report listing."""

import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

# Features list length is 27 as defined in constants.py
# Features include: numerical (margin, diem_thi, diem_moi_nhat, etc.)
# and one-hot encoded categories (nhom_nganh, vung_mien, phuong_thuc)


def train_models(X_train, y_train, X_test, y_test):
    """Fit scaler and classifiers, evaluate on hold-out test year."""
    # 1. Standardize numerical features
    scaler = StandardScaler().fit(X_train)
    Z_train = scaler.transform(X_train)
    Z_test = scaler.transform(X_test)

    # 2. Fit Decision Tree baseline
    dt = DecisionTreeClassifier(min_samples_leaf=5, random_state=42)
    dt.fit(Z_train, y_train)

    # 3. Fit Random Forest main model (100 trees, max depth 14)
    rf = RandomForestClassifier(
        n_estimators=100,
        min_samples_leaf=5,
        max_depth=14,
        n_jobs=-1,
        random_state=42,
    )
    rf.fit(Z_train, y_train)

    # 4. Evaluate on test split (year 2025)
    y_pred_rf = rf.predict(Z_test)
    acc = accuracy_score(y_test, y_pred_rf)
    report = classification_report(y_test, y_pred_rf, output_dict=True)

    # 5. Persist model and scaler for deployment
    joblib.dump(rf, "model.pkl")
    joblib.dump(scaler, "scaler.pkl")

    return acc, report
