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
    id_train, id_test = identity.iloc[train_idx], identity.iloc[test_idx]
    model = LogisticRegression(max_iter=1000)
    model.fit(x_train, y_train)
    probs = model.predict_proba(x_test)[:, 1]
    preds = (probs >= 0.5).astype(int)

    year_results: list[dict[str, object]] = []
    eval_rows = id_test.copy().reset_index(drop=True)
    eval_rows["y_true"] = y_test.to_numpy()
    eval_rows["y_pred"] = preds
    eval_rows["y_prob"] = probs
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

    report = {
        "rows": int(len(df)),
        "features": int(x.shape[1]),
        "seed": int(seed),
        "test_size": float(test_size),
        "accuracy": float(accuracy_score(y_test, preds)),
        "roc_auc": float(roc_auc_score(y_test, probs)) if y_test.nunique() > 1 else None,
        "yearly_results": year_results,
    }

    if report_path:
        Path(report_path).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    if predictions_path:
        out = pd.DataFrame({"y_true": y_test.to_numpy(), "y_pred": preds, "y_prob": probs})
        out.to_csv(predictions_path, index=False)

    return report
