# tests

import unittest
import tempfile
import os
import asyncio


try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass

from main import process_csv_folder

class TestProcessCSVFolder(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.orig_cwd = os.getcwd()
        os.chdir(self.tempdir.name)

    def tearDown(self):
        os.chdir(self.orig_cwd)
        self.tempdir.cleanup()

    def write_file(self, name: str, content: str):
        with open(name, 'w') as f:
            f.write(content)

    def read_output(self, name: str):
        with open(name, 'r') as f:
            return [line.strip() for line in f if line.strip()]

    def test_more_than_two_csv_returns_minus1(self):
        # Three CSVs should return -1 and produce no outputs
        for name in ['a.csv', 'b.csv', 'c.csv']:
            self.write_file(name, 'x,y\n1,2\n')
        result = asyncio.run(process_csv_folder(self.tempdir.name))
        self.assertEqual(result, -1)
        self.assertFalse(os.path.exists('a_output.csv'))
        self.assertFalse(os.path.exists('b_output.csv'))
        self.assertFalse(os.path.exists('c_output.csv'))

    def test_two_csv_file1_output(self):
        # Verify first file processing from prompt example
        file1 = 'apple,  34.12345 , -12.5\nbanana,42, hello\n'
        file2 = '   x,  y , z\n1.2345 , -1.234 ,world\n'
        self.write_file('file1.csv', file1)
        self.write_file('file2.csv', file2)
        asyncio.run(process_csv_folder(self.tempdir.name))
        out1 = self.read_output('file1_output.csv')
        self.assertEqual(out1, ['APPLE,34.123,0', 'BANANA,42,HELLO'])

    def test_two_csv_file2_output(self):
        # Verify second file processing from prompt example
        file1 = 'apple,  34.12345 , -12.5\nbanana,42, hello\n'
        file2 = '   x,  y , z\n1.2345 , -1.234 ,world\n'
        self.write_file('file1.csv', file1)
        self.write_file('file2.csv', file2)
        asyncio.run(process_csv_folder(self.tempdir.name))
        out2 = self.read_output('file2_output.csv')
        self.assertEqual(out2, ['X,Y,Z', '1.234,0,WORLD'])

    def test_ignore_inconsistent_rows(self):
        # Rows with mismatched columns should be ignored, no blank rows
        content = (
            'c1,c2,c3\n'
            '1,2,3\n'
            '4,5\n'      # too few
            '6,7,8,9\n'  # too many
            '7,8,9\n'    # valid
        )
        self.write_file('test.csv', content)
        self.write_file('other.csv', content)
        asyncio.run(process_csv_folder(self.tempdir.name))
        lines = self.read_output('test_output.csv')
        self.assertEqual(lines, ['C1,C2,C3', '1,2,3', '7,8,9'])

    def test_ignore_blank_rows(self):
        # Blank lines should be skipped, no inconsistent rows
        content = (
            'h1,h2\n'
            '\n'         # blank
            '1,2\n'      # valid
            '\n'         # blank
            '3,4\n'      # valid
        )
        self.write_file('a.csv', content)
        self.write_file('b.csv', content)
        asyncio.run(process_csv_folder(self.tempdir.name))
        lines = self.read_output('a_output.csv')
        self.assertEqual(lines, ['H1,H2', '1,2', '3,4'])

    def test_malformed_floats_become_zero(self):
        # Malformed floats result in 0
        content = 'v1,v2\nX,notfloat\n'
        self.write_file('vals.csv', content)
        self.write_file('other.csv', content)
        asyncio.run(process_csv_folder(self.tempdir.name))
        lines = self.read_output('vals_output.csv')
        self.assertIn('X,0', lines)

    def test_negative_floats_clamped_zero(self):
        # Negative floats should be clamped to 0
        content = 'v1,v2\nY,-0.0001\n'
        self.write_file('n.csv', content)
        self.write_file('m.csv', content)
        asyncio.run(process_csv_folder(self.tempdir.name))
        lines = self.read_output('n_output.csv')
        self.assertIn('Y,0', lines)

    def test_valid_floats_rounded_three_decimals(self):
        # Valid floats rounded to 3 decimals
        content = 'v1,v2\nZ,2.71828\n'
        self.write_file('p.csv', content)
        self.write_file('q.csv', content)
        asyncio.run(process_csv_folder(self.tempdir.name))
        lines = self.read_output('p_output.csv')
        self.assertIn('Z,2.718', lines)

    def test_ignore_non_csv_with_two_csv(self):
        # Two CSVs and one non-CSV file: only CSVs processed
        self.write_file('file1.csv', 'a,b\n1,2\n')
        self.write_file('file2.csv', 'x,y\n3,4\n')
        self.write_file('readme.txt', 'ignore me')
        asyncio.run(process_csv_folder(self.tempdir.name))
        self.assertTrue(os.path.exists('file1_output.csv'))
        self.assertTrue(os.path.exists('file2_output.csv'))

    def test_non_csv_not_generated(self):
        # Ensure non-CSV file does not get an output
        self.write_file('a.csv', 'x,y\n1,2\n')
        self.write_file('b.csv', 'x,y\n3,4\n')
        self.write_file('c.md', 'ignore')
        asyncio.run(process_csv_folder(self.tempdir.name))
        self.assertFalse(os.path.exists('c_output.md'))

if __name__ == '__main__':
    unittest.main()
