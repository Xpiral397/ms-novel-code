
"""This module transforms a CSV file."""

import pandas as pd


def transform_csv(filename: str) -> None:
    """Transform the input CSV.

    By computing columns E and F.
    Save the result.
    """
    df = pd.read_csv(filename)

    if df.empty:
        print("Empty CSV")
        return

    df.eval('E = A + B - C * D', inplace=True)

    group_means = df.groupby('Group')['E'].transform('mean')
    group_medians = df.groupby('Group')['E'].transform('median')

    df = df.assign(F=group_means.where(df['Group'] == 'X', group_medians))

    output_filename = 'output_' + filename
    df.to_csv(output_filename, index=False)


transform_csv('csv2_test.csv')

