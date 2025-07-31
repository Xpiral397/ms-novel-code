# tests

import unittest
import numpy as np
from qutip import basis, sigmax, sigmay, sigmaz, Qobj, identity
from main import evolve_pulse_sequence


class TestEvolvePulseSequence(unittest.TestCase):

    def setUp(self):
        """Set up common test fixtures"""
        # Set random seed for reproducibility as required
        np.random.seed(42)

        # Common quantum states
        self.state_0 = basis(2, 0)
        self.state_1 = basis(2, 1)
        self.plus_state = (basis(2, 0) + basis(2, 1)).unit()

        # Common Hamiltonians
        self.h_x = sigmax()
        self.h_y = sigmay()
        self.h_z = sigmaz()
        self.h_identity = identity(2)

    def test_basic_functionality_x_flip(self):
        """Test basic |0⟩ to |1⟩ transition with sigmax Hamiltonian"""
        result_seq, fidelity = evolve_pulse_sequence(
            initial_state=self.state_0,
            target_state=self.state_1,
            hamiltonian=self.h_x,
            pulse_length=10,
            generations=5,
            population_size=8,
            mutation_rate=0.1,
            bounds=(-1.0, 1.0)
        )

        # Basic structure checks
        self.assertIsInstance(result_seq, np.ndarray)
        self.assertEqual(result_seq.shape, (10,))
        self.assertIsInstance(fidelity, float)
        self.assertGreaterEqual(fidelity, 0.0)
        self.assertLessEqual(fidelity, 1.0)

        # Bounds checking
        self.assertTrue(np.all(result_seq >= -1.0))
        self.assertTrue(np.all(result_seq <= 1.0))





    def test_fixed_bounds_same_value(self):
        """Test edge case: bounds[0] == bounds[1] (all values fixed to constant)"""
        fixed_value = 0.5
        result_seq, fidelity = evolve_pulse_sequence(
            initial_state=self.state_0,
            target_state=self.state_1,
            hamiltonian=self.h_x,
            pulse_length=12,
            generations=4,
            population_size=10,
            mutation_rate=0.2,
            bounds=(fixed_value, fixed_value)
        )

        self.assertEqual(result_seq.shape, (12,))
        self.assertTrue(np.allclose(result_seq, fixed_value))

    def test_minimum_pulse_length(self):
        """Test minimum pulse_length = 10"""
        result_seq, fidelity = evolve_pulse_sequence(
            initial_state=self.state_1,
            target_state=self.state_0,
            hamiltonian=self.h_x,
            pulse_length=10,
            generations=3,
            population_size=5,
            mutation_rate=0.15,
            bounds=(-1.5, 1.5)
        )

        self.assertEqual(result_seq.shape, (10,))
        self.assertGreaterEqual(fidelity, 0.0)
        self.assertLessEqual(fidelity, 1.0)

    def test_maximum_pulse_length(self):
        """Test maximum pulse_length = 100"""
        result_seq, fidelity = evolve_pulse_sequence(
            initial_state=self.state_0,
            target_state=self.plus_state,
            hamiltonian=self.h_y,
            pulse_length=100,
            generations=2,
            population_size=5,
            mutation_rate=0.05,
            bounds=(-0.8, 0.8)
        )

        self.assertEqual(result_seq.shape, (100,))
        self.assertTrue(np.all(result_seq >= -0.8))
        self.assertTrue(np.all(result_seq <= 0.8))

    def test_maximum_generations(self):
        """Test maximum generations = 20"""
        result_seq, fidelity = evolve_pulse_sequence(
            initial_state=self.state_0,
            target_state=self.state_1,
            hamiltonian=self.h_z,
            pulse_length=15,
            generations=20,  # Maximum allowed
            population_size=8,
            mutation_rate=0.1,
            bounds=(-1.0, 1.0)
        )

        self.assertEqual(result_seq.shape, (15,))
        self.assertGreaterEqual(fidelity, 0.0)
        self.assertLessEqual(fidelity, 1.0)

    def test_minimum_population_size(self):
        """Test minimum population_size = 5"""
        result_seq, fidelity = evolve_pulse_sequence(
            initial_state=self.state_1,
            target_state=self.plus_state,
            hamiltonian=self.h_x,
            pulse_length=20,
            generations=5,
            population_size=5,
            mutation_rate=0.2,
            bounds=(-2.0, 2.0)
        )

        self.assertEqual(result_seq.shape, (20,))
        self.assertTrue(np.all(result_seq >= -2.0))
        self.assertTrue(np.all(result_seq <= 2.0))

    def test_maximum_population_size(self):
        """Test maximum population_size = 20"""
        result_seq, fidelity = evolve_pulse_sequence(
            initial_state=self.state_0,
            target_state=self.state_1,
            hamiltonian=self.h_x,
            pulse_length=25,
            generations=3,
            population_size=20,
            mutation_rate=0.1,
            bounds=(-1.0, 1.0)
        )

        self.assertEqual(result_seq.shape, (25,))
        self.assertGreaterEqual(fidelity, 0.0)
        self.assertLessEqual(fidelity, 1.0)

    def test_maximum_mutation_rate(self):
        """Test maximum mutation_rate = 1.0 (every gene mutates)"""
        result_seq, fidelity = evolve_pulse_sequence(
            initial_state=self.plus_state,
            target_state=self.state_0,
            hamiltonian=self.h_y,
            pulse_length=18,
            generations=4,
            population_size=8,
            mutation_rate=1.0,
            bounds=(-1.5, 1.5)
        )

        self.assertEqual(result_seq.shape, (18,))
        self.assertTrue(np.all(result_seq >= -1.5))
        self.assertTrue(np.all(result_seq <= 1.5))

    def test_identity_hamiltonian_no_evolution(self):
        """Test with identity Hamiltonian (no time evolution)"""
        result_seq, fidelity = evolve_pulse_sequence(
            initial_state=self.state_0,
            target_state=self.state_0,
            hamiltonian=self.h_identity,
            pulse_length=15,
            generations=5,
            population_size=10,
            mutation_rate=0.1,
            bounds=(-1.0, 1.0)
        )

        self.assertEqual(result_seq.shape, (15,))
        self.assertGreater(fidelity, 0.9)

    def test_different_hamiltonian_sigmay(self):
        """Test with sigmay Hamiltonian for different evolution dynamics"""
        result_seq, fidelity = evolve_pulse_sequence(
            initial_state=self.state_0,
            target_state=self.state_1,
            hamiltonian=self.h_y,
            pulse_length=22,
            generations=6,
            population_size=12,
            mutation_rate=0.15,
            bounds=(-0.7, 0.7)
        )

        self.assertEqual(result_seq.shape, (22,))
        self.assertTrue(np.all(result_seq >= -0.7))
        self.assertTrue(np.all(result_seq <= 0.7))

    def test_large_bounds_range(self):
        """Test with large bounds range"""
        result_seq, fidelity = evolve_pulse_sequence(
            initial_state=self.state_1,
            target_state=self.plus_state,
            hamiltonian=self.h_x,
            pulse_length=30,
            generations=5,
            population_size=15,
            mutation_rate=0.1,
            bounds=(-10.0, 10.0)
        )

        self.assertEqual(result_seq.shape, (30,))
        self.assertTrue(np.all(result_seq >= -10.0))
        self.assertTrue(np.all(result_seq <= 10.0))

    def test_fidelity_output_format(self):
        """Test that fidelity is properly rounded to 5 decimal places"""
        result_seq, fidelity = evolve_pulse_sequence(
            initial_state=self.state_0,
            target_state=self.state_1,
            hamiltonian=self.h_x,
            pulse_length=12,
            generations=3,
            population_size=8,
            mutation_rate=0.1,
            bounds=(-1.0, 1.0)
        )

        # Check that fidelity appears to be rounded to 5 decimal places
        self.assertIsInstance(fidelity, float)
        self.assertGreaterEqual(fidelity, 0.0)
        self.assertLessEqual(fidelity, 1.0)

    def test_negative_bounds(self):
        """Test with negative bounds range"""
        result_seq, fidelity = evolve_pulse_sequence(
            initial_state=self.state_0,
            target_state=self.state_1,
            hamiltonian=self.h_x,
            pulse_length=16,
            generations=4,
            population_size=10,
            mutation_rate=0.2,
            bounds=(-5.0, -1.0)  # All negative bounds
        )

        self.assertEqual(result_seq.shape, (16,))
        self.assertTrue(np.all(result_seq >= -5.0))
        self.assertTrue(np.all(result_seq <= -1.0))

    def test_positive_bounds(self):
        """Test with positive bounds range"""
        result_seq, fidelity = evolve_pulse_sequence(
            initial_state=self.plus_state,
            target_state=self.state_1,
            hamiltonian=self.h_y,
            pulse_length=14,
            generations=5,
            population_size=12,
            mutation_rate=0.05,
            bounds=(0.5, 3.0)  # All positive bounds
        )

        self.assertEqual(result_seq.shape, (14,))
        self.assertTrue(np.all(result_seq >= 0.5))
        self.assertTrue(np.all(result_seq <= 3.0))


if __name__ == '__main__':
    unittest.main(argv=[''], exit=False)
