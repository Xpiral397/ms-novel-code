"""Run evolutionary algorithm experiments using GA, DE, or ES strategies."""

import random
import numpy as np
from typing import List, Tuple, Callable, Dict
from abc import ABC, abstractmethod


class BaseEvolutionaryAlgorithm(ABC):
    """Abstract base class for evolutionary algorithm strategies."""

    @abstractmethod
    def evolve(
        self,
        population: List[List[float]],
        fitness_function: Callable[[List[float]], float],
        bounds: Tuple[List[float], List[float]],
        mutation_rate: float,
        crossover_rate: float,
        selection_strategy: "BaseSelectionStrategy",
        rng: random.Random
    ) -> List[List[float]]:
        """Perform one generation of evolution."""
        pass


class BaseMetricLogger(ABC):
    """Abstract base class for metric logging."""

    @abstractmethod
    def log(
        self,
        population: List[List[float]],
        fitnesses: List[float],
        generation: int
    ) -> None:
        """Log statistics for each generation."""
        pass

    @abstractmethod
    def get_metrics(self) -> Dict[str, List[float]]:
        """Return recorded metrics as a dictionary."""
        pass


class BaseSelectionStrategy(ABC):
    """Abstract base class for parent selection strategies."""

    @abstractmethod
    def select(
        self,
        population: List[List[float]],
        fitnesses: List[float],
        k: int,
        rng: random.Random
    ) -> List[List[float]]:
        """Select k parents from the population."""
        pass


class FitnessWrapper:
    """Wrap a fitness function to support maximization via inversion."""

    def __init__(self, func: Callable[[List[float]],
                 float], maximize: bool = False):
        """Initialize with a fitness function and mode (maximize/minimize)."""
        self.func = func
        self.maximize = maximize

    def __call__(self, x: List[float]) -> float:
        """Inverting the fitness function if maximization is enabled."""
        value = self.func(x)
        return -value if self.maximize else value


class SimpleLogger(BaseMetricLogger):
    """Log best, average fitness, and population diversity per generation."""

    def __init__(self):
        """Initialize the SimpleLogger with empty metric containers."""
        self.metrics = {
            "best_fitness": [],
            "avg_fitness": [],
            "diversity": []
        }

    def log(self, population, fitnesses, generation):
        """Log statistics for a generation."""
        best = min(fitnesses)
        avg = sum(fitnesses) / len(fitnesses)
        mean_vector = [
            sum(ind[i] for ind in population) / len(population)
            for i in range(len(population[0]))
        ]
        diversity = sum(
            np.linalg.norm(np.array(ind) - np.array(mean_vector))
            for ind in population
        ) / len(population)

        self.metrics["best_fitness"].append(best)
        self.metrics["avg_fitness"].append(avg)
        self.metrics["diversity"].append(diversity)

    def get_metrics(self):
        """Return the logged metric dictionary."""
        return self.metrics


class TournamentSelection(BaseSelectionStrategy):
    """Tournament-based parent selection strategy."""

    def __init__(self, tournament_size=2):
        """Initialize with the size of each tournament group."""
        self.tournament_size = tournament_size

    def select(self, population, fitnesses, k, rng):
        """Select k individuals using tournament selection."""
        selected = []
        for _ in range(k):
            candidates = rng.choices(
                list(zip(population, fitnesses)), k=self.tournament_size
            )
            winner = min(candidates, key=lambda x: x[1])[0]
            selected.append(winner[:])
        return selected


class RouletteSelection(BaseSelectionStrategy):
    """Roulette wheel (fitness-proportionate) selection strategy."""

    def select(self, population, fitnesses, k, rng):
        """Select k individuals using roulette wheel selection."""
        max_fit = max(fitnesses)
        inv_fits = [max_fit - f + 1e-8 for f in fitnesses]
        total = sum(inv_fits)
        probs = [f / total for f in inv_fits]
        selected = rng.choices(population, weights=probs, k=k)
        return [ind[:] for ind in selected]


class RandomSelection(BaseSelectionStrategy):
    """Randomly select parents without considering fitness."""

    def select(self, population, fitnesses, k, rng):
        """Select k individuals randomly from the population."""
        return [rng.choice(population)[:] for _ in range(k)]


class GAAlgorithm(BaseEvolutionaryAlgorithm):
    """Standard Genetic Algorithm implementation."""

    def evolve(
        self, population, fitness_function, bounds, mutation_rate,
        crossover_rate, selection_strategy, rng
    ):
        """Evolve the population using genetic algorithm operations."""
        new_population = []
        dim = len(bounds[0])
        fitnesses = [fitness_function(ind) for ind in population]
        parents = selection_strategy.select(
            population, fitnesses, len(population), rng
        )

        for i in range(0, len(population), 2):
            p1 = parents[i]
            p2 = parents[(i + 1) % len(parents)]

            if rng.random() < crossover_rate:
                point = rng.randint(1, dim - 1)
                child1 = p1[:point] + p2[point:]
                child2 = p2[:point] + p1[point:]
            else:
                child1, child2 = p1[:], p2[:]

            for child in (child1, child2):
                for j in range(dim):
                    if rng.random() < mutation_rate:
                        child[j] = rng.uniform(bounds[0][j], bounds[1][j])
                clipped = [
                    max(bounds[0][j], min(bounds[1][j], child[j]))
                    for j in range(dim)
                ]
                new_population.append(clipped)
                if len(new_population) == len(population):
                    break

        return new_population


class DEAlgorithm(BaseEvolutionaryAlgorithm):
    """Differential Evolution implementation."""

    def evolve(
        self, population, fitness_function, bounds, mutation_rate,
        crossover_rate, selection_strategy, rng
    ):
        """Evolve the population using differential evolution."""
        dim = len(bounds[0])
        new_population = []

        for i in range(len(population)):
            a, b, c = rng.sample(
                [ind for j, ind in enumerate(population) if j != i], 3
            )
            mutant = [a[j] + mutation_rate * (b[j] - c[j]) for j in range(dim)]
            target = population[i]

            trial = [
                mutant[j] if rng.random() < crossover_rate else target[j]
                for j in range(dim)
            ]
            trial = [
                max(bounds[0][j], min(bounds[1][j], trial[j]))
                for j in range(dim)
            ]

            if fitness_function(trial) <= fitness_function(target):
                new_population.append(trial)
            else:
                new_population.append(target)

        return new_population


class ESAlgorithm(BaseEvolutionaryAlgorithm):
    """Evolution Strategy implementation."""

    def evolve(
        self, population, fitness_function, bounds, mutation_rate,
        crossover_rate, selection_strategy, rng
    ):
        """Evolve the population using evolution strategy."""
        dim = len(bounds[0])
        fitnesses = [fitness_function(ind) for ind in population]
        new_population = []
        parents = selection_strategy.select(
            population, fitnesses, len(population), rng
        )

        for parent in parents:
            child = parent[:]
            for i in range(dim):
                if rng.random() < mutation_rate:
                    sigma = (bounds[1][i] - bounds[0][i]) * 0.1
                    child[i] += rng.gauss(0, sigma)
                    child[i] = max(bounds[0][i], min(bounds[1][i], child[i]))
            new_population.append(child)

        return new_population


class ExperimentBuilder:
    """Builder for configuring and running evolutionary experiments."""

    def __init__(self):
        """Initialize all configuration variables."""
        self.population_size = None
        self.num_generations = None
        self.algorithm = None
        self.fitness_function = None
        self.problem_bounds = None
        self.metric_logger = None
        self.mutation_rate = None
        self.crossover_rate = None
        self.selection_strategy = None
        self.random_seed = None
        self.maximize = False

    def configure(
        self,
        population_size: int,
        num_generations: int,
        algorithm: BaseEvolutionaryAlgorithm,
        fitness_function: Callable[[List[float]], float],
        problem_bounds: Tuple[List[float], List[float]],
        metric_logger: BaseMetricLogger,
        mutation_rate: float,
        crossover_rate: float,
        selection_strategy: BaseSelectionStrategy,
        random_seed: int,
        maximize: bool = False
    ) -> "ExperimentBuilder":
        """Configure all parameters of the experiment."""
        self.population_size = population_size
        self.num_generations = num_generations
        self.algorithm = algorithm
        self.fitness_function = FitnessWrapper(fitness_function, maximize)
        self.problem_bounds = problem_bounds
        self.metric_logger = metric_logger
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.selection_strategy = selection_strategy
        self.random_seed = random_seed
        self.maximize = maximize
        return self

    def run(self) -> Tuple[
        List[float],
        float,
        Dict[str, List[float]],
        List[List[List[float]]],
        List[List[float]]
    ]:
        """Run the experiment and return best solution, metrics, and all gens"""
        rng = random.Random(self.random_seed)
        np.random.seed(self.random_seed)
        dim = len(self.problem_bounds[0])

        population = [
            [
                rng.uniform(self.problem_bounds[0][j], self.problem_bounds[1][j])
                for j in range(dim)
            ]
            for _ in range(self.population_size)
        ]

        all_generations = [population[:]]

        for gen in range(self.num_generations):
            fitnesses = [self.fitness_function(ind) for ind in population]
            self.metric_logger.log(population, fitnesses, gen)
            population = self.algorithm.evolve(
                population,
                self.fitness_function,
                self.problem_bounds,
                self.mutation_rate,
                self.crossover_rate,
                self.selection_strategy,
                rng
            )
            all_generations.append(population[:])

        final_fitnesses = [self.fitness_function(ind) for ind in population]
        best_idx = final_fitnesses.index(min(final_fitnesses))
        best_solution = population[best_idx]
        best_fitness = (
            -final_fitnesses[best_idx] if self.maximize else final_fitnesses[best_idx]
        )

        return (
            best_solution,
            best_fitness,
            self.metric_logger.get_metrics(),
            all_generations,
            population
        )


def run_experiment(
    population_size: int,
    num_generations: int,
    algorithm: BaseEvolutionaryAlgorithm,
    fitness_function: Callable[[List[float]], float],
    problem_bounds: Tuple[List[float], List[float]],
    metric_logger: BaseMetricLogger,
    mutation_rate: float,
    crossover_rate: float,
    selection_strategy: BaseSelectionStrategy,
    builder: ExperimentBuilder,
    random_seed: int,
    maximize: bool = False
) -> Tuple[
    List[float],
    float,
    Dict[str, List[float]],
    List[List[List[float]]],
    List[List[float]]
]:
    """Run a configured evolutionary algorithm experiment"""
    builder.configure(
        population_size,
        num_generations,
        algorithm,
        fitness_function,
        problem_bounds,
        metric_logger,
        mutation_rate,
        crossover_rate,
        selection_strategy,
        random_seed,
        maximize
    )
    return builder.run()
