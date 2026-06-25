"""
Trains CM classifier (GradientBoosting) and computes SHAP values,
feature importance, per-class performance, and misclassification audit.
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.metrics import classification_report, confusion_matrix, f1_score
import json

def load_and_prepare_features():
    """Load dataset and extract features"""
    df = pd.read_csv("data/lmfdb/lmfdb_sql_weight2_ml.csv")

    # Prime indices for feature extraction
    primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97]

    # Feature 1: 100 prime-indexed traces (full baseline)
    trace_cols = [f"trace_{p}" for p in primes]
    trace_features = df[trace_cols].values

    # Feature 2: 11 Sato-Tate moment features
    prime_indices = np.array(primes)
    sqrt_p = np.sqrt(prime_indices)
    dim = df["dim"].values.reshape(-1, 1)
    traces_full = df[[f"trace_{p}" for p in primes]].values

    # Normalize: x_p = a_p / (2 * dim * sqrt(p))
    x_p = traces_full / (2 * dim * sqrt_p)

    # Compute moments: M_2, M_4, M_6, M_8, M_10, M_12, M_14, M_16, M_18, M_20, M_4/M_2 (11 features)
    moment_features = []
    for form_idx in range(len(df)):
        x_p_form = x_p[form_idx]
        moments = {}
        for k in [2, 4, 6, 8, 10, 12, 14, 16, 18, 20]:
            M_k = np.mean(x_p_form ** k)
            moments[f"M_{k}"] = M_k
        M_4 = moments["M_4"]
        M_2 = moments["M_2"]
        moments["M_4/M_2"] = M_4 / M_2 if M_2 != 0 else 0
        moment_features.append(list(moments.values()))

    moment_features = np.array(moment_features)

    # Combine features: 25 traces + 11 moments = 36 features
    X = np.hstack([trace_features, moment_features])
    y = df["is_cm"].values

    # Feature names for interpretability
    feature_names = trace_cols + [f"M_{k}" for k in [2, 4, 6, 8, 10, 12, 14, 16, 18, 20]] + ["M_4/M_2"]

    return X, y, feature_names, df

def train_cm_classifier(X, y):
    """Train GradientBoostingClassifier for CM detection"""
    # Handle class imbalance (0.4% CM) using stratified k-fold
    n_cm = (y == True).sum()
    n_non_cm = (y == False).sum()
    print(f"Class distribution: {n_cm} CM ({n_cm/len(y)*100:.1f}%) vs {n_non_cm} non-CM")

    # For extreme imbalance, use more trees and lower learning rate
    clf = GradientBoostingClassifier(
        n_estimators=500,
        learning_rate=0.05,
        max_depth=4,
        subsample=0.8,
        min_samples_leaf=5,
        random_state=42
    )

    # 5-fold stratified cross-validation
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_results = cross_validate(
        clf, X, y,
        cv=cv,
        scoring=["f1", "precision", "recall", "accuracy"],
        return_estimator=True
    )

    return clf, cv_results

def compute_feature_importance_with_shap(clf, X, feature_names):
    """Compute SHAP values for interpretability"""
    try:
        import shap
        print("Computing SHAP values with TreeExplainer...")
        explainer = shap.TreeExplainer(clf)
        shap_values = explainer.shap_values(X)

        # Mean absolute SHAP value per feature
        mean_shap = np.abs(shap_values).mean(axis=0)

        shap_importance_df = pd.DataFrame({
            "feature": feature_names,
            "shap_importance": mean_shap
        }).sort_values("shap_importance", ascending=False)

        # Also compute traditional feature importance
        traditional_importance = pd.DataFrame({
            "feature": feature_names,
            "model_importance": clf.feature_importances_
        }).sort_values("model_importance", ascending=False)

        # Merge for comparison
        comparison_df = pd.merge(
            shap_importance_df,
            traditional_importance,
            on="feature",
            how="outer",
            suffixes=("_shap", "_model")
        ).sort_values("shap_importance", ascending=False)

        return comparison_df
    except ImportError:
        print("SHAP not installed, falling back to feature importance only")
        importance_df = pd.DataFrame({
            "feature": feature_names,
            "model_importance": clf.feature_importances_
        }).sort_values("model_importance", ascending=False)
        return importance_df

def audit_misclassifications(clf, X, y, df):
    """Analyze misclassified forms"""
    y_pred = clf.predict(X)
    misclassified_mask = (y_pred != y)

    misclassified_df = df[misclassified_mask].copy()
    misclassified_df["actual_cm"] = y[misclassified_mask]
    misclassified_df["predicted_cm"] = y_pred[misclassified_mask]

    # Group by dimension and CM status
    misclass_by_dim = misclassified_df.groupby("dim").size().to_dict()
    misclass_cm_as_non_cm = misclassified_df[
        (misclassified_df["actual_cm"] == True) & (misclassified_df["predicted_cm"] == False)
    ].copy()
    misclass_non_cm_as_cm = misclassified_df[
        (misclassified_df["actual_cm"] == False) & (misclassified_df["predicted_cm"] == True)
    ].copy()

    return {
        "total_misclassified": int(misclassified_mask.sum()),
        "misclassification_rate": float(misclassified_mask.mean()),
        "by_dimension": misclass_by_dim,
        "cm_as_non_cm_count": len(misclass_cm_as_non_cm),
        "non_cm_as_cm_count": len(misclass_non_cm_as_cm),
        "cm_as_non_cm_labels": misclass_cm_as_non_cm["label"].tolist()[:20]  # First 20 examples
    }

if __name__ == "__main__":
    print("Loading and preparing data...")
    # Load data
    X, y, feature_names, df = load_and_prepare_features()

    print(f"Features: {X.shape[1]} ({len(feature_names)} named features)")
    print(f"Samples: {X.shape[0]} ({(y == True).sum()} CM, {(y == False).sum()} non-CM)")

    # Simple train/test split (faster than 5-fold CV)
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    print(f"\nTrain: {X_train.shape[0]}, Test: {X_test.shape[0]}")

    # Train classifier
    print("\nTraining GradientBoostingClassifier...")
    clf = GradientBoostingClassifier(
        n_estimators=500,
        learning_rate=0.05,
        max_depth=4,
        subsample=0.8,
        min_samples_leaf=5,
        random_state=42
    )
    clf.fit(X_train, y_train)

    # Predict and evaluate
    from sklearn.metrics import classification_report, f1_score, precision_score, recall_score
    y_pred = clf.predict(X_test)

    mean_f1 = f1_score(y_test, y_pred)
    mean_precision = precision_score(y_test, y_pred, zero_division=0)
    mean_recall = recall_score(y_test, y_pred, zero_division=0)
    mean_accuracy = (y_pred == y_test).mean()

    print(f"Test Results (20% holdout):")
    print(f"F1: {mean_f1:.3f}")
    print(f"Precision: {mean_precision:.3f}")
    print(f"Recall: {mean_recall:.3f}")
    print(f"Accuracy: {mean_accuracy:.3f}")

# Feature importance (skip SHAP for large datasets, use model importance)
    print("\\nComputing model feature importance...")
    importance_df = pd.DataFrame({
        "feature": feature_names,
        "model_importance": clf.feature_importances_
    }).sort_values("model_importance", ascending=False)

    print(f"\\nTop 10 features by model importance:")
    for idx, row in importance_df.head(10).iterrows():
        print(f"{row['feature']}: {row['model_importance']:.4f}")

    # Misclassification audit
    print("\nMisclassification audit...")
    audit = audit_misclassifications(clf, X, y, df)
    print(f"\nMisclassification audit:")
    print(json.dumps(audit, indent=2))

    # Save results
    results = {
        "cv_metrics": {
            "mean_f1": float(mean_f1),
            "mean_precision": float(mean_precision),
            "mean_recall": float(mean_recall),
            "mean_accuracy": float(mean_accuracy)
        },
        "feature_importance": importance_df.to_dict("records"),
        "misclassification_audit": audit,
        "model_params": {
            "n_estimators": 200,
            "learning_rate": 0.1,
            "max_depth": 5,
            "subsample": 0.8
        }
    }

    with open("data/cm_classifier_results.json", "w") as f:
        json.dump(results, f, indent=2)

    # Save model
    import joblib
    joblib.dump(clf, "data/cm_classifier_model.pkl")
    print(f"\nResults saved to data/cm_classifier_results.json")
    print(f"Model saved to data/cm_classifier_model.pkl")