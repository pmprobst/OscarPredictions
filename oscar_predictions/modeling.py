"""Clean production modeling pipeline for Oscar predictions."""

from __future__ import annotations

import json
from pathlib import Path

from oscar_predictions.workspace import DataWorkspace


def run_model(
    workspace: DataWorkspace,
    *,
    seed: int = 42,
    test_size: float = 0.25,
    report_path: str | None = None,
    predictions_path: str | None = None,
) -> dict:
    import pandas as pd
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, roc_auc_score
    from sklearn.model_selection import train_test_split

    data_path = workspace.movie_totals
    df = pd.read_csv(data_path)
    if "oscar_win" not in df.columns:
        raise ValueError(
            f"Expected target column 'oscar_win' in {data_path}. "
            "Ensure movies.csv includes oscar_win before running modeling."
        )

    y = pd.to_numeric(df["oscar_win"], errors="coerce").fillna(0).astype(int)
    drop_cols = {"oscar_win", "title", "url"}
    x = df.drop(columns=[c for c in drop_cols if c in df.columns])
    for col in x.columns:
        x[col] = pd.to_numeric(x[col], errors="coerce").fillna(0)

    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=test_size, random_state=seed, stratify=y if y.nunique() > 1 else None
    )
    model = LogisticRegression(max_iter=1000)
    model.fit(x_train, y_train)
    probs = model.predict_proba(x_test)[:, 1]
    preds = (probs >= 0.5).astype(int)

    report = {
        "rows": int(len(df)),
        "features": int(x.shape[1]),
        "seed": int(seed),
        "test_size": float(test_size),
        "accuracy": float(accuracy_score(y_test, preds)),
        "roc_auc": float(roc_auc_score(y_test, probs)) if y_test.nunique() > 1 else None,
    }

    if report_path:
        Path(report_path).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    if predictions_path:
        out = pd.DataFrame({"y_true": y_test.to_numpy(), "y_pred": preds, "y_prob": probs})
        out.to_csv(predictions_path, index=False)

    return report
