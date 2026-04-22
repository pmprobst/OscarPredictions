"""Clean production modeling pipeline for Oscar predictions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from oscar_predictions.workspace import DataWorkspace

if TYPE_CHECKING:
    from pandas import DataFrame


def _build_yearly_results(eval_rows: "DataFrame") -> list[dict[str, object]]:
    """Build per-year nominee lists and predicted vs actual winners from scored rows."""
    year_results: list[dict[str, object]] = []
    for year, group in eval_rows.groupby("year", sort=True):
        nominees = [
            {"title": str(row.title), "predicted_win_pct": float(row.y_prob * 100.0), "actual_win": bool(row.y_true)}
            for row in group.sort_values("y_prob", ascending=False).itertuples()
        ]
        predicted_winner = nominees[0]["title"] if nominees else None
        actual_winner = next((nom["title"] for nom in nominees if nom["actual_win"]), None)
        year_results.append(
            {
                "year": int(year),
                "predicted_winner": predicted_winner,
                "actual_winner": actual_winner,
                "nominees": nominees,
            }
        )
    return year_results


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
    from sklearn.model_selection import GroupShuffleSplit

    data_path = workspace.movie_totals
    df = pd.read_csv(data_path)
    if "oscar_win" not in df.columns:
        raise ValueError(
            f"Expected target column 'oscar_win' in {data_path}. "
            "Ensure movies.csv includes oscar_win before running modeling."
        )

    y = pd.to_numeric(df["oscar_win"], errors="coerce").fillna(0).astype(int)
    identity = df[[c for c in ("title", "year") if c in df.columns]].copy()
    if "title" not in identity.columns:
        identity["title"] = "(unknown title)"
    if "year" not in identity.columns:
        identity["year"] = 0
    identity["title"] = identity["title"].fillna("(unknown title)").astype(str)
    identity["year"] = pd.to_numeric(identity["year"], errors="coerce").fillna(0).astype(int)
    drop_cols = {"oscar_win", "title", "url"}
    x = df.drop(columns=[c for c in drop_cols if c in df.columns])
    for col in x.columns:
        x[col] = pd.to_numeric(x[col], errors="coerce").fillna(0)

    groups = identity["year"].to_numpy()
    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
    train_idx, test_idx = next(splitter.split(x, y, groups=groups))
    x_train, x_test = x.iloc[train_idx], x.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
    model = LogisticRegression(max_iter=100000)
    model.fit(x_train, y_train)
    probs_test = model.predict_proba(x_test)[:, 1]
    preds_test = (probs_test >= 0.5).astype(int)

    probs_all = model.predict_proba(x)[:, 1]
    preds_all = (probs_all >= 0.5).astype(int)

    test_idx_set = set(test_idx.tolist())
    n_rows = len(x)
    split_labels = ["test" if i in test_idx_set else "train" for i in range(n_rows)]

    eval_all = identity.reset_index(drop=True).copy()
    eval_all["y_true"] = y.reset_index(drop=True).to_numpy()
    eval_all["y_pred"] = preds_all
    eval_all["y_prob"] = probs_all
    eval_all["split"] = split_labels

    year_results = _build_yearly_results(eval_all)

    report = {
        "rows": int(len(df)),
        "features": int(x.shape[1]),
        "seed": int(seed),
        "test_size": float(test_size),
        "accuracy": float(accuracy_score(y_test, preds_test)),
        "roc_auc": float(roc_auc_score(y_test, probs_test)) if y_test.nunique() > 1 else None,
        "yearly_results": year_results,
    }

    if report_path:
        Path(report_path).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    if predictions_path:
        out = eval_all[["year", "title", "y_true", "y_prob", "y_pred", "split"]].copy()
        out.to_csv(predictions_path, index=False)

    return report
