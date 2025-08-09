# tests

"""
Unit tests for the clean_and_impute function.
"""
import os
import tempfile
import unittest

import pandas as pd

from main import clean_and_impute


class TestCleanAndImpute(unittest.TestCase):
    """
    Test suite for the clean_and_impute function.
    """

    def setUp(self) -> None:
        """
        Create a temporary directory and switch to it before each test.
        """
        self.tempdir = tempfile.TemporaryDirectory()
        self.original_cwd = os.getcwd()
        os.chdir(self.tempdir.name)

    def tearDown(self) -> None:
        """
        Restore the original directory, clean temporary dir after each test.
        """
        os.chdir(self.original_cwd)
        self.tempdir.cleanup()

    def write_csv(self, filename: str, df: pd.DataFrame) -> None:
        """
        Write the given DataFrame to a CSV file without an index.

        Args:
            filename: The name of the CSV file to write.
            df: The DataFrame to save.
        """
        df.to_csv(filename, index=False)

    def test_threshold_out_of_bounds(self) -> None:
        """
        Threshold outside [0, 1] must return an empty DataFrame & log an error.
        """
        df, log = clean_and_impute('dummy.csv', {}, -0.1)
        self.assertTrue(df.empty)
        self.assertIn('Invalid threshold value', log[0])

        df, log = clean_and_impute('dummy.csv', {}, 1.5)
        self.assertTrue(df.empty)
        self.assertIn('Invalid threshold value', log[0])

    def test_file_not_found(self) -> None:
        """
        A missing file should return an empty DataFrame and log a read failure.
        """
        df, log = clean_and_impute('nofile.csv', {'col': 'mean'}, 0.5)
        self.assertTrue(df.empty)
        self.assertIn('Failed to read CSV', log[0])

    def test_empty_csv(self) -> None:
        """
        CSV with only headers should return empty DataFrame & log the condition.
        """
        df_input = pd.DataFrame(columns=['a', 'b'])
        self.write_csv('empty.csv', df_input)
        df, log = clean_and_impute('empty.csv', {}, 0.5)
        self.assertTrue(df.empty)
        self.assertIn('CSV is empty or contains only headers', log[0])

    def test_skip_nonexistent_column_rule(self) -> None:
        """
          Absent of imputation rules for columns in CSV must be skipped with a
          warning log.
        """
        df_input = pd.DataFrame({'x': [1, None, 3]})
        self.write_csv('data.csv', df_input)
        df, log = clean_and_impute('data.csv', {'y': 'mean'}, 0.5)
        self.assertIn("Skipped non-existent column 'y'", log[0])

    def test_mean_and_median_imputation(self) -> None:
        """
        Numeric columns should be correctly imputed using mean and median
        strategies.
        """
        df_input = pd.DataFrame({
            'a': [1, None, 3],
            'b': [None, 2, 4]
        })
        self.write_csv('in.csv', df_input)
        df, log = clean_and_impute('in.csv', {'a': 'mean', 'b': 'median'}, 1.0)
        self.assertAlmostEqual(df.loc[1, 'a'], 2)
        self.assertAlmostEqual(df.loc[0, 'b'], 2)
        self.assertIn('Column a: filled 1 missing values with mean=', log[0])
        self.assertIn('Column b: filled 1 missing values with median=', log[1])

    def test_mode_imputation_and_high_cardinality(self) -> None:
        """
        Mode imputation should fill missing values, and high-cardinality columns
         should be dropped.
        """
        df_input = pd.DataFrame({
            'c': ['x', None, 'x', 'y', 'z',
                  'w', 'v', 'u', 't', 's']
        })
        self.write_csv('mode.csv', df_input)
        df, log = clean_and_impute('mode.csv', {'c': 'mode'}, 1.0)
        self.assertEqual(df.loc[1, 'c'], 'x')
        self.assertTrue(any('Dropped column' in entry for entry in log))

    def test_drop_entirely_nan_column(self) -> None:
        """
        Columns that are entirely NaN should be dropped and logged.
        """
        df_input = pd.DataFrame({
            'd': [None, None, None],
            'e': [1, 2, 3]
        })
        self.write_csv('nan.csv', df_input)
        df, log = clean_and_impute('nan.csv', {'d': 'mode', 'e': 'mean'}, 1.0)
        self.assertNotIn('d', df.columns)
        self.assertIn("Dropped column 'd' due to being entirely NaN", log)

    def test_drop_columns_over_threshold(self) -> None:
        """
        Columns with missing-value fraction above the threshold should be dropped.
        """
        df_input = pd.DataFrame({
            'f': [1, None, None, 4],
            'g': [1, 2, 3, 4]
        })
        self.write_csv('thr.csv', df_input)
        df, log = clean_and_impute('thr.csv', {'f': 'mean', 'g': 'mean'}, 0.25)
        self.assertNotIn('f', df.columns)
        self.assertIn(
            "Dropped column 'f' due to missing data > threshold=0.25",
            log
        )

    def test_drop_rows_over_threshold(self) -> None:
        """
        Rows with missing-value fraction above the threshold should be dropped.
        """
        df_input = pd.DataFrame({
            'h': [1, None, 3],
            'i': [None, None, None]
        })
        self.write_csv('rows.csv', df_input)
        df, log = clean_and_impute('rows.csv', {'h': 'mean', 'i': 'mode'}, 0.5)
        self.assertNotIn(1, df.index)
        self.assertIn(
            'Dropped row 1 due to missing data > threshold=0.5',
            log
        )

    def test_no_missing_values(self) -> None:
        """
        When no missing values exist, log that nothing was changed.
        """
        df_input = pd.DataFrame({
            'j': [1, 2, 3],
            'k': ['a', 'b', 'c']
        })
        self.write_csv('nomiss.csv', df_input)
        df, log = clean_and_impute('nomiss.csv', {}, 0.5)
        self.assertIn(
            'No missing values found, nothing was changed',
            log
        )

    def test_output_file_created(self) -> None:
        """
        Ensure the cleaned CSV file is saved and the final log entry is correct.
        """
        df_input = pd.DataFrame({
            'l': [1, None],
            'm': ['x', None]
        })
        self.write_csv('out.csv', df_input)
        _, log = clean_and_impute('out.csv', {'l': 'mean', 'm': 'mode'}, 1.0)
        self.assertTrue(os.path.exists('cleaned_out.csv'))
        self.assertIn(
            "Saved cleaned DataFrame to 'cleaned_out.csv'",
            log[-1]
        )


if __name__ == '__main__':
    unittest.main(argv=[''])
