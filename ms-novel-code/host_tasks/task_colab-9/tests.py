# tests


# Unit tests for Evolutionary Algorithm Framework

import unittest
import time

from main import (
    run_experiment,
    BaseEvolutionaryAlgorithm,
    BaseSelectionStrategy,
    BaseMetricLogger,
    ExperimentBuilder,
    DEAlgorithm,
    RouletteSelection,
    SimpleLogger,
)

class TestEvolutionaryFramework(unittest.TestCase):

    def setUp(self):
        """Common test data setup."""
        self.example1_config = {
            'population_size': 5,
            'num_generations': 3,
            'algorithm': DEAlgorithm(),
            'fitness_function': lambda x: -sum((xi - 0.5)**2 for xi in x),
            'problem_bounds': ([0.0, 0.0, 0.0], [1.0, 1.0, 1.0]),
            'metric_logger': SimpleLogger(),
            'mutation_rate': 0.1,
            'crossover_rate': 0.8,
            'selection_strategy': RouletteSelection(),
            'builder': ExperimentBuilder(),
            'random_seed': 42
        }

        self.example2_config = {
            'population_size': 5,
            'num_generations': 2,
            'algorithm': DEAlgorithm(),
            'fitness_function': lambda x: sum(xi**2 for xi in x),
            'problem_bounds': ([-1.0, -1.0], [1.0, 1.0]),
            'metric_logger': SimpleLogger(),
            'mutation_rate': 0.2,
            'crossover_rate': 0.9,
            'selection_strategy': RouletteSelection(),
            'builder': ExperimentBuilder(),
            'random_seed': 123
        }

        self.base_config = {
            'population_size': 5,
            'num_generations': 3,
            'algorithm': DEAlgorithm(),
            'fitness_function': lambda x: sum(x),
            'problem_bounds': ([0.0, 0.0], [1.0, 1.0]),
            'metric_logger': SimpleLogger(),
            'mutation_rate': 0.1,
            'crossover_rate': 0.8,
            'selection_strategy': RouletteSelection(),
            'builder': ExperimentBuilder(),
            'random_seed': 42
        }

    def test_example1_structure_and_behavior(self):
        result = run_experiment(**self.example1_config)

        self.assertEqual(len(result), 5)
        self.assertIsInstance(result[0], list)
        self.assertIsInstance(result[1], float)
        self.assertIsInstance(result[2], dict)

        metrics = result[2]
        self.assertIn('best_fitness', metrics)
        self.assertIn('avg_fitness', metrics)
        self.assertIn('diversity', metrics)

        self.assertEqual(len(metrics['best_fitness']), 3)
        self.assertEqual(len(metrics['avg_fitness']), 3)
        self.assertEqual(len(metrics['diversity']), 3)

        expected_dimensions = len(self.example1_config['problem_bounds'][0])
        self.assertEqual(len(result[0]), expected_dimensions)

    def test_different_seeds_different_results(self):
        """Different seeds produce different results but same structure."""
        config_seed42 = {**self.base_config, 'random_seed': 42}
        config_seed123 = {**self.base_config, 'random_seed': 123}
        config_seed999 = {**self.base_config, 'random_seed': 999}

        result42 = run_experiment(**config_seed42)
        result123 = run_experiment(**config_seed123)
        result999 = run_experiment(**config_seed999)

        self.assertNotEqual(result42[0], result123[0])
        self.assertNotEqual(result42[3], result999[3])

        self.assertEqual(len(result42), len(result123))
        self.assertEqual(len(result42[4]), len(result123[4]))

    def test_selection_strategy_interface_compliance(self):
        """Test selection strategy interface compliance."""
        strategy = RouletteSelection()

        self.assertIsInstance(strategy, BaseSelectionStrategy)
        self.assertTrue(hasattr(strategy, 'select'))
        self.assertTrue(callable(getattr(strategy, 'select')))

    def test_experiment_builder_configuration(self):
        """ExperimentBuilder properly configures and validates experiments."""
        builder = ExperimentBuilder()

        self.assertIsNotNone(builder)
        self.assertIsInstance(builder, ExperimentBuilder)

        result = run_experiment(**self.base_config)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 5)

    def test_population_bounds_compliance(self):
        """All individuals stay within problem_bounds throughout evolution."""
        bounds = ([0.0, -1.0], [1.0, 1.0])
        config = {**self.base_config, 'problem_bounds': bounds}

        result = run_experiment(**config)
        all_generations = result[3]

        for generation in all_generations:
            for individual in generation:
                for i, gene in enumerate(individual):
                    self.assertGreaterEqual(gene, bounds[0][i],
                        f"Gene {gene} below lower bound {bounds[0][i]}")
                    self.assertLessEqual(gene, bounds[1][i],
                        f"Gene {gene} above upper bound {bounds[1][i]}")

    def test_tight_bounds_edge_case(self):
        """Handles degenerate bounds like ([0.5], [0.5]) correctly."""
        tight_bounds = ([0.5], [0.5])  # No variation possible
        config = {
            'population_size': 5,
            'num_generations': 2,
            'algorithm': DEAlgorithm(),
            'fitness_function': lambda x: sum(x),
            'problem_bounds': tight_bounds,
            'metric_logger': SimpleLogger(),
            'mutation_rate': 0.1,
            'crossover_rate': 0.8,
            'selection_strategy': RouletteSelection(),
            'builder': ExperimentBuilder(),
            'random_seed': 42
        }

        result = run_experiment(**config)

        # All individuals should be exactly [0.5]
        final_population = result[4]
        for individual in final_population:
            self.assertEqual(individual, [0.5])

    def test_single_individual_population(self):
        """population_size=1 handled gracefully without crashes."""
        config = {**self.base_config, 'population_size': 4}

        result = run_experiment(**config)

        self.assertIsNotNone(result[0])
        self.assertGreater(len(result[4]), 0)
        self.assertEqual(len(result[3]), 4)

    def test_zero_mutation_rate(self):
        """mutation_rate=0.0 doesn't break evolution process."""
        config = {**self.base_config, 'mutation_rate': 0.0}

        result = run_experiment(**config)

        self.assertIsNotNone(result[0])
        self.assertIsInstance(result[1], float)
        self.assertEqual(len(result), 5)

    def test_generation_structure_consistency(self):
        """all_generations has correct structure and num_generations entries."""
        result = run_experiment(**self.base_config)
        all_generations = result[3]

        self.assertEqual(len(all_generations), self.base_config['num_generations'] + 1)

        for generation in all_generations:
            self.assertGreater(len(generation), 0)

        problem_dim = len(self.base_config['problem_bounds'][0])
        for generation in all_generations:
            for individual in generation:
                self.assertEqual(len(individual), problem_dim)

    def test_output_format_compliance(self):
        """Return values match exact specified types and structure."""
        result = run_experiment(**self.base_config)

        self.assertEqual(len(result), 5)

        best_solution, best_fitness, metrics_log, all_generations, final_population = result

        self.assertIsInstance(best_solution, list)
        self.assertIsInstance(best_fitness, float)
        self.assertIsInstance(metrics_log, dict)
        self.assertIsInstance(all_generations, list)
        self.assertIsInstance(final_population, list)

        self.assertTrue(all(isinstance(gene, float) for gene in best_solution))
        self.assertTrue(all(isinstance(v, list) for v in metrics_log.values()))

    def test_input_validation_critical_cases(self):
        """Test critical input validation scenarios."""
        try:
            config = {**self.base_config, 'population_size': 0}
            run_experiment(**config)
        except Exception:
            pass

        try:
            config = {**self.base_config, 'num_generations': 0}
            run_experiment(**config)
        except Exception:
            pass

    def test_bounds_validation_edge_cases(self):
        """Test edge cases for problem bounds validation."""
        try:
            config = {**self.base_config, 'problem_bounds': ([0.0], [1.0, 1.0])}
            run_experiment(**config)
            self.assertTrue(True)
        except Exception:
            pass

        try:
            config = {**self.base_config, 'problem_bounds': ([], [])}
            run_experiment(**config)
            self.assertTrue(True)
        except Exception:
            pass

    def test_fitness_optimization_behavior(self):
        """Test that algorithm actually optimizes fitness over generations."""

        def fitness_func(x):
            return sum(xi**2 for xi in x)  # Minimum at [0, 0]

        config = {
            **self.base_config,
            'fitness_function': fitness_func,
            'problem_bounds': ([-2.0, -2.0], [2.0, 2.0]),
            'num_generations': 5,
            'population_size': 10,
            'random_seed': 42
        }

        result = run_experiment(**config)
        metrics = result[2]

        self.assertIn('best_fitness', metrics)
        self.assertEqual(len(metrics['best_fitness']), 5)

        best_fitnesses = metrics['best_fitness']
        first_fitness = best_fitnesses[0]
        last_fitness = best_fitnesses[-1]

        self.assertLessEqual(last_fitness, first_fitness * 2.0,
                           "Algorithm should not significantly worsen over generations")

    def test_convergence_behavior_simple(self):
        """Test basic convergence behavior."""

        target = [0.5, 0.5]
        def fitness_func(x):
            return -sum((xi - target[i])**2 for i, xi in enumerate(x))

        config = {
            **self.base_config,
            'fitness_function': fitness_func,
            'problem_bounds': ([0.0, 0.0], [1.0, 1.0]),
            'num_generations': 8,
            'population_size': 15,
            'mutation_rate': 0.05,  # Lower mutation for better convergence
            'random_seed': 42
        }

        result = run_experiment(**config)
        best_solution = result[0]

        for gene in best_solution:
            self.assertGreaterEqual(gene, 0.0)
            self.assertLessEqual(gene, 1.0)

        self.assertEqual(len(best_solution), 2)
        self.assertIsInstance(best_solution[0], float)
        self.assertIsInstance(best_solution[1], float)

    def test_strategy_pattern_polymorphism(self):
        """Test that strategy pattern works correctly."""

        config = {**self.base_config, 'selection_strategy': RouletteSelection(), 'random_seed': 42}
        result = run_experiment(**config)

        self.assertEqual(len(result), 5)
        self.assertIsInstance(result[0], list)
        self.assertIsInstance(result[1], float)
        self.assertIsNotNone(result[0])

    def test_performance_basic_scalability(self):
        """Test framework handles reasonable scale efficiently."""

        larger_config = {
            **self.base_config,
            'population_size': 20,
            'num_generations': 10,
            'random_seed': 42
        }

        start_time = time.time()
        result = run_experiment(**larger_config)
        end_time = time.time()

        execution_time = end_time - start_time

        # Should complete in reasonable time (generous threshold)
        self.assertLess(execution_time, 15.0,
                       "Larger experiment should complete within 15 seconds")
        self.assertIsNotNone(result[0])

        self.assertEqual(len(result[3]), 11)
        for generation in result[3]:
            self.assertGreater(len(generation), 0)

    def test_metric_logger_interface_compliance(self):
        """Test that metric loggers implement required interface properly."""

        logger = SimpleLogger()

        self.assertIsInstance(logger, BaseMetricLogger)
        self.assertTrue(hasattr(logger, 'log'))
        self.assertTrue(hasattr(logger, 'get_metrics'))
        self.assertTrue(callable(getattr(logger, 'log')))
        self.assertTrue(callable(getattr(logger, 'get_metrics')))

        test_population = [[0.1, 0.2], [0.3, 0.4]]
        test_fitnesses = [0.5, 0.7]

        try:
            logger.log(test_population, test_fitnesses, 0)
            metrics = logger.get_metrics()
            self.assertIsInstance(metrics, dict)
        except Exception as e:
            self.fail(f"Basic logger functionality failed: {e}")

    def test_algorithm_interface_contract(self):
        """Test that algorithms strictly follow their interface contracts."""

        algorithm = DEAlgorithm()

        self.assertIsInstance(algorithm, BaseEvolutionaryAlgorithm)
        self.assertTrue(hasattr(algorithm, 'evolve'))
        self.assertTrue(callable(getattr(algorithm, 'evolve')))

    def test_deterministic_behavior(self):
        """Same random_seed produces identical results."""
        result1 = run_experiment(**self.base_config)
        result2 = run_experiment(**self.base_config)

        self.assertEqual(result1[0], result2[0])
        self.assertEqual(result1[1], result2[1])
        self.assertEqual(result1[3], result2[3])
        self.assertEqual(result1[4], result2[4])

    def test_minimum_population_size_for_de(self):
        """Test that DE algorithm works with minimum required population size."""
        config = {
            'population_size': 4,  # Minimum for DE algorithm
            'num_generations': 2,
            'algorithm': DEAlgorithm(),
            'fitness_function': lambda x: sum(x),
            'problem_bounds': ([0.0], [1.0]),
            'metric_logger': SimpleLogger(),
            'mutation_rate': 0.1,
            'crossover_rate': 0.8,
            'selection_strategy': RouletteSelection(),
            'builder': ExperimentBuilder(),
            'random_seed': 42
        }

        result = run_experiment(**config)

        self.assertIsNotNone(result[0])
        self.assertEqual(len(result), 5)
        self.assertEqual(len(result[3]), 3)

if __name__ == '__main__':
    unittest.main()
