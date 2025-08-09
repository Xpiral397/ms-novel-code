
"""Module for cleaning and imputing missing data in a CSV file."""

import os
import pandas as pd


def clean_and_impute(
    filepath: str,
    imputation_rules: dict,
    threshold: float
) -> tuple[pd.DataFrame, list[str]]:
    """
    Clean and impute missing values in the given CSV file.

    Args:
        filepath (str): Path to the CSV file.
        imputation_rules (dict): Dictionary mapping column names to
            imputation strategies ("mean", "median", or "mode").
        threshold (float): Max allowed missing ratio for rows/columns.

    Returns:
        tuple[pd.DataFrame, list[str]]: Cleaned DataFrame and a log list.
    """
    log = []

    if threshold < 0 or threshold > 1:
        log.append(
            "Invalid threshold value: must be between 0 and 1 inclusive."
        )
        return pd.DataFrame(), log

    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        log.append(f"Failed to read CSV: {e}")
        return pd.DataFrame(), log

    if df.empty:
        log.append("CSV is empty or contains only headers.")
        return df, log

    changes_made = False

    for col, strategy in imputation_rules.items():
        if col not in df.columns:
            log.append(
                f"Skipped non-existent column '{col}' for imputation"
            )
            continue

        if df[col].isnull().sum() == 0:
            continue

        if strategy not in ["mean", "median", "mode"]:
            log.append(
                f"Invalid imputation strategy '{strategy}' for column '{col}'"
            )
            continue

        if df[col].isnull().all():
            continue

        if (
            not pd.api.types.is_numeric_dtype(df[col])
            and strategy in ["mean", "median"]
        ):
            log.append(
                f"Cannot apply '{strategy}' imputation on "
                f"non-numeric column '{col}'"
            )
            continue

        filled_count = df[col].isnull().sum()

        if strategy == "mean":
            mean_value = df[col].mean()
            df[col].fillna(mean_value, inplace=True)
            log.append(
                f"Column {col}: filled {filled_count} missing values "
                f"with mean={mean_value}"
            )
            changes_made = True

        elif strategy == "median":
            median_value = df[col].median()
            df[col].fillna(median_value, inplace=True)
            log.append(
                f"Column {col}: filled {filled_count} missing values "
                f"with median={median_value}"
            )
            changes_made = True

        elif strategy == "mode":
            if df[col].nunique() / len(df) > 0.9:
                log.append(
                    f"Cannot apply mode imputation on high-cardinality "
                    f"column '{col}'"
                )
                continue

            if not df[col].mode().empty:
                mode_value = df[col].mode().iloc[0]
                df[col].fillna(mode_value, inplace=True)
                log.append(
                    f"Column {col}: filled {filled_count} missing values "
                    f"with mode='{mode_value}'"
                )
                changes_made = True

    cols_to_drop = []
    for col in df.columns:
        if df[col].nunique() / len(df) > 0.9:
            cols_to_drop.append(col)
            log.append(f"Dropped column '{col}' due to >90% uniqueness")
            changes_made = True

    df.drop(columns=cols_to_drop, inplace=True)

    entirely_nan_cols = df.columns[df.isnull().all()]
    for col in entirely_nan_cols:
        df.drop(columns=[col], inplace=True)
        log.append(f"Dropped column '{col}' due to being entirely NaN")
        changes_made = True

    for col in df.columns[df.isnull().mean() > threshold]:
        df.drop(columns=[col], inplace=True)
        log.append(
            f"Dropped column '{col}' due to missing data > threshold="
            f"{threshold}"
        )
        changes_made = True

    rows_to_drop = df.index[df.isnull().mean(axis=1) > threshold]
    for index in rows_to_drop:
        df.drop(index=index, inplace=True)
        log.append(
            f"Dropped row {index} due to missing data > threshold="
            f"{threshold}"
        )
        changes_made = True

    if not changes_made and not any(df.isnull().sum() > 0):
        log.append("No missing values found, nothing was changed")

    base_filename = os.path.basename(filepath)
    new_filename = f"cleaned_{base_filename}"
    df.to_csv(new_filename, index=False)
    log.append(f"Saved cleaned DataFrame to '{new_filename}'")

    return df, log


imputation_rules = {
    "age": "mean",
    "income": "median",
    "gender": "mode",
    "city": "mode",
    "empty_col": "mode"
}

clean_and_impute('test.csv', imputation_rules, 0.3)

