#!/usr/bin/env python3
"""ZanderEtAlFishing — Command-Line Prediction Testing Program.

Interactive and batch testing tool for the hybrid ML phishing detection engine.
"""

import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from ml_engine.model_loader import ModelLoader
from ml_engine.predictor import PhishingPredictor


def print_banner():
    banner = """========================================
       ZANDERETALFISHING
       HYBRID ML DETECTION ENGINE
========================================"""
    print(banner)


def main():
    print_banner()

    try:
        # Load artifacts with verbose status feedback
        artifacts = ModelLoader.load_artifacts()
        print("[OK] Logistic Regression loaded")
        print("[OK] LightGBM loaded")
        print("[OK] Word vectorizer loaded")
        print("[OK] Character vectorizer loaded")
        print("[OK] Stylometric scaler loaded")

        predictor = PhishingPredictor(artifacts=artifacts)

        lr_pct = int(predictor.w_lr * 100)
        lgb_pct = int(predictor.w_lgb * 100)
        print(f"\nEnsemble Configuration:")
        print(f"Logistic Regression: {lr_pct}%")
        print(f"LightGBM: {lgb_pct}%")
        print(f"Decision Threshold: {predictor.threshold:.2f}")

        print("\nModel ready for inference.")

        # Interactive loop
        while True:
            print("\nEnter email (or 'quit'/'exit' to stop):")
            try:
                line = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting ZanderEtAlFishing tester.")
                break

            if not line:
                print("[Warning] Empty input. Please enter email content.")
                continue

            if line.lower() in ("quit", "exit", "q"):
                print("Exiting ZanderEtAlFishing tester.")
                break

            print("\nAnalyzing email...")
            try:
                result = predictor.predict(line)
                print(f"\nClassification: {result['classification']}")
                print(f"Phishing Probability: {result['phishing_probability']:.4f}")
                print(f"LR Probability: {result['logistic_regression_probability']:.4f}")
                print(f"LightGBM Probability: {result['lightgbm_probability']:.4f}")
                print(f"Inference Time: {result['inference_time_ms']:.2f} ms")
            except Exception as e:
                print(f"[Error] Prediction failed: {e}")

    except Exception as ex:
        print(f"\n[FATAL] Failed to initialize engine: {ex}")
        sys.exit(1)


if __name__ == "__main__":
    main()

