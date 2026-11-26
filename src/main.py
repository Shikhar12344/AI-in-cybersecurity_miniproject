"""
AI-Driven Cyber Threat Awareness and Detection Prototype
Academic Project: Cyber Threat Detection using the TON_IoT Network Dataset
"""

import os
import glob
import time
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.tree import DecisionTreeClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
    ConfusionMatrixDisplay
)


def main():
    print("=" * 70)
    print("  AI-Driven Cyber Threat Awareness & Detection Prototype (TON_IoT)")
    print("  Academic Cybersecurity Practical Project: Machine Learning Pipeline")
    print("=" * 70)

    # -------------------------------------------------------------
    # Task 2: Dataset Acquisition & Exploratory Data Analysis (EDA)
    # -------------------------------------------------------------
    print("\n[+] Task 2: Ingesting TON_IoT Dataset...")
    
    # Priority 1: Check local project data directory
    local_data_path = os.path.join(os.path.dirname(__file__), "..", "data", "train_test_network.csv")
    selected_csv = None
    if os.path.exists(local_data_path):
        selected_csv = os.path.abspath(local_data_path)
    else:
        # Priority 2: Check kagglehub cache or download
        try:
            import kagglehub
            dataset_dir = kagglehub.dataset_download("arnobbhowmik/ton-iot-network-dataset")
            csv_files = glob.glob(os.path.join(dataset_dir, "**", "*.csv"), recursive=True)
            if csv_files:
                selected_csv = csv_files[0]
        except Exception:
            # Fallback search in user cache
            user_cache = os.path.expanduser(r"~/.cache/kagglehub/datasets/arnobbhowmik/ton-iot-network-dataset")
            csv_files = glob.glob(os.path.join(user_cache, "**", "*.csv"), recursive=True)
            if csv_files:
                selected_csv = csv_files[0]

    if not selected_csv or not os.path.exists(selected_csv):
        raise FileNotFoundError("Could not locate train_test_network.csv in local data/ or kagglehub cache.")

    print(f"[+] Loaded telemetry CSV: {selected_csv} ({os.path.getsize(selected_csv)/(1024*1024):.2f} MB)")

    # Load representative sample (100,000 records for high-fidelity evaluation)
    df = pd.read_csv(selected_csv, nrows=100000, low_memory=False)
    print(f"[+] Successfully loaded records: {df.shape[0]:,} rows x {df.shape[1]} columns")

    print("\n--- Binary Class Distribution (label: 0=Normal, 1=Threat) ---")
    if 'label' in df.columns:
        print(df['label'].value_counts(dropna=False))

    if 'type' in df.columns:
        print("\n--- Attack Type Telemetry Breakdown ---")
        print(df['type'].value_counts(dropna=False))

    # Generate EDA Plots and save to file
    print("\n[+] Generating Task 2 EDA Visualizations...")
    sns.set_theme(style="darkgrid", palette="mako")
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    # Plot 1: Count plot of normal vs suspicious
    label_names = {0: 'Normal (0)', 1: 'Suspicious / Attack (1)'}
    plot_labels = df['label'].map(label_names) if df['label'].dtype in [np.int64, int] else df['label']
    sns.countplot(x=plot_labels, ax=axes[0], palette=["#2ec4b6", "#e71d36"])
    axes[0].set_title("Traffic Distribution: Normal vs. Suspicious Activities", fontweight="bold", fontsize=13)
    axes[0].set_xlabel("Traffic Category", fontweight="bold")
    axes[0].set_ylabel("Flow Count", fontweight="bold")
    for p in axes[0].patches:
        axes[0].annotate(f'{int(p.get_height()):,}', (p.get_x() + p.get_width() / 2., p.get_height()),
                         ha='center', va='center', xytext=(0, 6), textcoords='offset points', fontweight='bold')

    # Plot 2: Distribution of key network feature
    key_feat = 'duration' if 'duration' in df.columns else 'src_bytes'
    temp_feat = pd.to_numeric(df[key_feat], errors='coerce').fillna(0)
    log_feat = np.log1p(temp_feat[temp_feat >= 0])
    sns.histplot(data=df, x=log_feat, hue='label', kde=True, bins=35, ax=axes[1], palette=["#2ec4b6", "#e71d36"], element="step")
    axes[1].set_title(f"Distribution of Network Feature: log1p({key_feat})", fontweight="bold", fontsize=13)
    axes[1].set_xlabel(f"log(1 + {key_feat})", fontweight="bold")
    axes[1].set_ylabel("Density / Frequency", fontweight="bold")

    plt.tight_layout()
    plt.savefig("eda_plots.png", dpi=200)
    plt.close()
    print("[+] Saved clean EDA visualization to eda_plots.png")

    # -------------------------------------------------------------
    # Task 3: Machine Learning Threat Classification (Decision Tree)
    # -------------------------------------------------------------
    print("\n[+] Task 3: Preprocessing Telemetry Data (Strict Train/Test Isolation)...")
    df_clean = df.replace(['-', '?', ' -', '- '], np.nan)
    target_col = 'label'
    y = df_clean[target_col].astype(int)

    # Prevent target and identity leakage (drop IP addresses, timestamps, attack sub-labels)
    cols_to_drop = [c for c in ['ts', 'src_ip', 'dst_ip', 'type', 'label'] if c in df_clean.columns]
    X_raw = df_clean.drop(columns=cols_to_drop)

    cat_cols = X_raw.select_dtypes(include=['object', 'category']).columns.tolist()
    num_cols = X_raw.select_dtypes(include=[np.number]).columns.tolist()

    # Stratified Split 80% Train, 20% Test prior to encoding/scaling
    X_train_raw, X_test_raw, y_train, y_test = train_test_split(
        X_raw, y, test_size=0.20, random_state=42, stratify=y
    )
    print(f"[+] Train split: {len(X_train_raw):,} samples | Test split: {len(X_test_raw):,} samples")

    X_train = X_train_raw.copy()
    X_test = X_test_raw.copy()

    # 1. Numerical Imputation and Standardization (fitted strictly on train)
    for c in num_cols:
        med = pd.to_numeric(X_train[c], errors='coerce').median()
        val = 0 if pd.isna(med) else med
        X_train[c] = pd.to_numeric(X_train[c], errors='coerce').fillna(val)
        X_test[c] = pd.to_numeric(X_test[c], errors='coerce').fillna(val)

    scaler = StandardScaler()
    X_train[num_cols] = scaler.fit_transform(X_train[num_cols])
    X_test[num_cols] = scaler.transform(X_test[num_cols])

    # 2. Categorical Imputation and Label Encoding (handling unseen categories)
    for c in cat_cols:
        X_train[c] = X_train[c].fillna('unknown').astype(str)
        X_test[c] = X_test[c].fillna('unknown').astype(str)

        le = LabelEncoder()
        X_train[c] = le.fit_transform(X_train[c])
        class_mapping = {cls: idx for idx, cls in enumerate(le.classes_)}
        X_test[c] = X_test[c].map(class_mapping).fillna(len(le.classes_)).astype(int)

    print(f"[+] Feature matrix prepared with {X_train.shape[1]} engineered features.")

    # Tuned Decision Tree: entropy criterion, max_depth=15, min_samples_split=4, min_samples_leaf=2
    print("\n[+] Training Tuned Decision Tree Classifier (criterion='entropy', max_depth=15, min_samples_split=4, min_samples_leaf=2)...")
    dt_start = time.time()
    dt = DecisionTreeClassifier(
        criterion='entropy',
        max_depth=15,
        min_samples_split=4,
        min_samples_leaf=2,
        random_state=42
    )
    dt.fit(X_train, y_train)
    dt_time = time.time() - dt_start

    dt_preds = dt.predict(X_test)
    dt_acc = accuracy_score(y_test, dt_preds)
    dt_prec = precision_score(y_test, dt_preds, zero_division=0)
    dt_rec = recall_score(y_test, dt_preds, zero_division=0)
    dt_f1 = f1_score(y_test, dt_preds, zero_division=0)

    print("=" * 60)
    print("       TUNED DECISION TREE CLASSIFIER EVALUATION")
    print("=" * 60)
    print(f"Training Time : {dt_time:.4f} seconds")
    print(f"Accuracy      : {dt_acc * 100:.2f}%")
    print(f"Precision     : {dt_prec:.4f}")
    print(f"Recall        : {dt_rec:.4f}")
    print(f"F1-Score      : {dt_f1:.4f}")
    print("=" * 60)
    print("\nDetailed Classification Report:")
    print(classification_report(y_test, dt_preds, target_names=['Normal', 'Suspicious']))

    # -------------------------------------------------------------
    # Task 4: Deep Learning Threat Classification (MLP Neural Net)
    # -------------------------------------------------------------
    # Tuned MLP: hidden_layer_sizes=(128, 64), alpha=0.0005, max_iter=30, batch_size=256
    print("\n[+] Task 4: Training Tuned Multi-Layer Perceptron (MLP) Neural Network (layers=(128,64), alpha=0.0005, max_iter=30)...")
    mlp_start = time.time()
    mlp = MLPClassifier(
        hidden_layer_sizes=(128, 64),
        activation='relu',
        solver='adam',
        alpha=0.0005,
        batch_size=256,
        max_iter=30,
        random_state=42,
        early_stopping=True
    )
    mlp.fit(X_train, y_train)
    mlp_time = time.time() - mlp_start

    mlp_preds = mlp.predict(X_test)
    mlp_acc = accuracy_score(y_test, mlp_preds)
    mlp_prec = precision_score(y_test, mlp_preds, zero_division=0)
    mlp_rec = recall_score(y_test, mlp_preds, zero_division=0)
    mlp_f1 = f1_score(y_test, mlp_preds, zero_division=0)

    print("=" * 60)
    print("   TUNED MLP NEURAL NETWORK (DEEP LEARNING) EVALUATION")
    print("=" * 60)
    print(f"Training Time : {mlp_time:.4f} seconds")
    print(f"Accuracy      : {mlp_acc * 100:.2f}%")
    print(f"Precision     : {mlp_prec:.4f}")
    print(f"Recall        : {mlp_rec:.4f}")
    print(f"F1-Score      : {mlp_f1:.4f}")
    print("=" * 60)
    print("\nDetailed Classification Report:")
    print(classification_report(y_test, mlp_preds, target_names=['Normal', 'Suspicious']))

    # Model Performance & Architecture Comparison
    comparison_df = pd.DataFrame({
        'Metric': ['Training Time (s)', 'Accuracy (%)', 'Precision', 'Recall', 'F1-Score'],
        'Decision Tree (ML)': [
            f"{dt_time:.3f}s", f"{dt_acc*100:.2f}%", f"{dt_prec:.4f}", f"{dt_rec:.4f}", f"{dt_f1:.4f}"
        ],
        'MLP Neural Net (DL)': [
            f"{mlp_time:.3f}s", f"{mlp_acc*100:.2f}%", f"{mlp_prec:.4f}", f"{mlp_rec:.4f}", f"{mlp_f1:.4f}"
        ]
    })
    print("\n" + "=" * 30 + " ML vs. DL COMPARISON " + "=" * 30)
    print(comparison_df.to_string(index=False))
    print("=" * 82)

    # -------------------------------------------------------------
    # Task 5: Ethical Reflection & Aggressive Posture Simulation
    # -------------------------------------------------------------
    print("\n[+] Task 5: Running Aggressive Security Posture Simulation...")
    mlp_probs = mlp.predict_proba(X_test)[:, 1]
    strict_thresh = 0.30
    strict_preds = (mlp_probs >= strict_thresh).astype(int)

    cm_strict = confusion_matrix(y_test, strict_preds)
    tn, fp, fn, tp = cm_strict.ravel()
    total_normal = tn + fp
    fp_pct = (fp / total_normal) * 100

    print("=" * 65)
    print(f" SIMULATION: Threat Threshold set to > {strict_thresh*100:.0f}%")
    print("=" * 65)
    print(f"True Negatives (Legitimate Allowed)       : {tn:,}")
    print(f"False Positives (Legitimate Blocked)      : {fp:,}")
    print(f"False Negatives (Attacks Missed)          : {fn:,}")
    print(f"True Positives (Attacks Blocked)          : {tp:,}")
    print("-" * 65)
    print(f"Total Legitimate User Sessions Tested     : {total_normal:,}")
    print(f"Exact False Positives (Disrupted Users)   : {fp:,} ({fp_pct:.2f}%)")
    print(f"Attack Recall (Attacks Successfully Caught): {(tp / (tp + fn)) * 100:.2f}%")
    print("=" * 65)

    # Save Confusion Matrix Visual Comparison
    print("\n[+] Generating Confusion Matrix Comparison Plot...")
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    cm_default = confusion_matrix(y_test, mlp_preds)

    ConfusionMatrixDisplay(confusion_matrix=cm_default, display_labels=['Normal', 'Suspicious']).plot(
        ax=axes[0], cmap='Blues', colorbar=False
    )
    axes[0].set_title("Standard Posture (Threshold = 0.50)", fontweight='bold', fontsize=12)
    axes[0].grid(False)

    ConfusionMatrixDisplay(confusion_matrix=cm_strict, display_labels=['Normal', 'Suspicious']).plot(
        ax=axes[1], cmap='Reds', colorbar=False
    )
    axes[1].set_title(f"Aggressive Posture (Threshold = {strict_thresh:.2f})", fontweight='bold', fontsize=12)
    axes[1].grid(False)

    plt.tight_layout()
    plt.savefig("confusion_matrix_simulation.png", dpi=200)
    plt.close()
    print("[+] Saved confusion matrix visualization to confusion_matrix_simulation.png")

    print("\n[✔] Execution completed successfully!")


if __name__ == "__main__":
    main()
