# tests

"""
Unit tests for transform_csv, ensuring correct E/F computation, file output, and edge case handling based on the prompt requirements.
"""
import os
import tempfile
import unittest
import pandas as pd
from io import StringIO
import sys

from transform_module import transform_csv


class TestTransformCsv(unittest.TestCase):
    """
    Test suite for transform_csv function.
    """

    def setUp(self) -> None:
        """
        Prepare a temporary directory for test isolation.
        """
        self.tempdir = tempfile.TemporaryDirectory()
        self.orig_cwd = os.getcwd()
        os.chdir(self.tempdir.name)

    def tearDown(self) -> None:
        """
        Clean up temporary directory and restore working directory.
        """
        os.chdir(self.orig_cwd)
        self.tempdir.cleanup()

    def write_csv(self, filename: str, content: str) -> None:
        """
        Write raw CSV content to a file without index.

        Args:
            filename: Name of the CSV file to create.
            content: CSV text to write.
        """
        with open(filename, 'w') as f:
            f.write(content)

    def find_output_file(self) -> str:
        """
        Locate the output CSV generated by transform_csv.

        Returns:
            Filename of the transformed CSV.
        """
        files = [f for f in os.listdir('.') if f.endswith('.csv') and f != 'input.csv' and f != 'empty.csv' and f != 'nanrow.csv']
        self.assertEqual(len(files), 1, 'Expected exactly one output CSV file')
        return files[0]

    def test_example_transformation(self) -> None:
        """
        Verify E = A + B - C * D and F uses mean for Group X and median for Group Y.
        """
        csv_in = (
            "A,B,C,D,Group\n"
            "1,2,3,4,X\n"
            "5,,2,1,Y\n"
            ",,1,1,X\n"
            "4,4,4,4,Y\n"
        )
        self.write_csv('input.csv', csv_in)
        transform_csv('input.csv')
        out = self.find_output_file()
        df = pd.read_csv(out)
        # Compute expected E values
        expected_e = [1+2-3*4, None, None, 4+4-4*4]
        # Group stats: X rows E valid = [-9], mean=-9; Y rows E valid=[?, -8] median = -8
        expected_f = [-9, -8, -9, -8]
        for idx, (e_exp, f_exp) in enumerate(zip(expected_e, expected_f)):
            if e_exp is None:
                self.assertTrue(pd.isna(df.loc[idx, 'E']))
            else:
                self.assertAlmostEqual(df.loc[idx, 'E'], float(e_exp))
            self.assertAlmostEqual(df.loc[idx, 'F'], float(f_exp))

    def test_empty_csv(self) -> None:
        """
        An empty CSV should print 'Empty CSV' and not produce an output file.
        """
        self.write_csv('empty.csv', 'A,B,C,D,Group\n')
        captured = StringIO()
        sys_stdout = sys.stdout
        sys.stdout = captured
        transform_csv('empty.csv')
        sys.stdout = sys_stdout
        self.assertIn('Empty CSV', captured.getvalue())
        files = [f for f in os.listdir('.') if f.endswith('.csv')]
        self.assertEqual(files, ['empty.csv'])

    def test_all_nan_row(self) -> None:
        """
        Rows with all NaN in A-D must not break evaluation and should yield NaN E.
        """
        csv_in = (
            "A,B,C,D,Group\n"
            ",,, ,X\n"
        )
        self.write_csv('nanrow.csv', csv_in)
        transform_csv('nanrow.csv')
        out = self.find_output_file()
        df = pd.read_csv(out)
        self.assertTrue(pd.isna(df.loc[0, 'E']))
        self.assertTrue(pd.isna(df.loc[0, 'F']))

    def test_missing_file_raises(self) -> None:
        """
        Supplying a non-existent file path should raise FileNotFoundError.
        """
        with self.assertRaises(FileNotFoundError):
            transform_csv('nofile.csv')

    def test_partial_nan_computation(self) -> None:
        """
        Partial NaNs in A-D yield NaN E but F computed per group mean/median.
        """
        csv_in = (
            "A,B,C,D,Group\n"
            "2,3, , ,X\n"
            "2,2,1,1,X\n"
        )
        self.write_csv('input.csv', csv_in)
        transform_csv('input.csv')
        out = self.find_output_file()
        df = pd.read_csv(out)
        self.assertTrue(pd.isna(df.loc[0, 'E']))
        # Only valid E is row1 => 2+2-1*1=3, so mean=median=3
        self.assertAlmostEqual(df.loc[0, 'F'], 3.0)
        self.assertAlmostEqual(df.loc[1, 'E'], 3.0)

    def test_original_columns_retained(self) -> None:
        """
        Output CSV must preserve A,B,C,D,Group in order before E and F.
        """
        self.write_csv('input.csv', 'A,B,C,D,Group\n1,1,1,1,X\n')
        transform_csv('input.csv')
        out = self.find_output_file()
        df = pd.read_csv(out)
        self.assertEqual(list(df.columns), ['A', 'B', 'C', 'D', 'Group', 'E', 'F'])

    def test_output_file_exists(self) -> None:
        """
        After transformation, a new CSV file should exist.
        """
        self.write_csv('data.csv', 'A,B,C,D,Group\n1,2,3,4,X\n')
        transform_csv('data.csv')
        out = self.find_output_file()
        self.assertTrue(os.path.exists(out))

    def test_group_statistics(self) -> None:
        """
        F should use mean for group X and median for group Y explicitly.
        """
        csv_in = (
            "A,B,C,D,Group\n"
            "1,1,1,1,X\n"
            "2,2,2,2,X\n"
            "3,3,3,3,Y\n"
            "4,4,4,4,Y\n"
        )
        self.write_csv('input.csv', csv_in)
        transform_csv('input.csv')
        out = self.find_output_file()
        df = pd.read_csv(out)
        # E for X rows: [1+1-1*1=1, 2+2-2*2=0] mean = 0.5 -> F
        x_f = df[df['Group']=='X']['F'].iloc[0]
        self.assertAlmostEqual(x_f, 0.5)
        # E for Y rows: [3+3-3*3=-3, 4+4-4*4=-4] median = avg of middle => -3.5
        y_f = df[df['Group']=='Y']['F'].iloc[0]
        self.assertAlmostEqual(y_f, -3.5)

if __name__ == '__main__':
    unittest.main()
