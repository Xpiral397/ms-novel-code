
import numpy as np
from qutip import Qobj, mesolve, basis, sigmax, fidelity
from typing import Tuple


def evolve_pulse_sequence(
    initial_state: Qobj,
    target_state: Qobj,
    hamiltonian: Qobj,
    pulse_length: int,
    generations: int,
    population_size: int,
    mutation_rate: float,
    bounds: tuple[float, float]
) -> Tuple[np.ndarray, float]:
    """Run GA to find pulse sequence that maximizes fidelity to target state."""

    # Validate all constraints dynamically
    if not isinstance(initial_state, Qobj) or not isinstance(target_state, Qobj) or not isinstance(hamiltonian, Qobj):
        raise TypeError("initial_state, target_state, and hamiltonian must be Qobj instances.")
    if not isinstance(pulse_length, int) or not (10 <= pulse_length <= 100):
        raise ValueError("pulse_length must be an int in [10, 100].")
    if not isinstance(generations, int) or not (1 <= generations <= 20):
        raise ValueError("generations must be an int in [1, 20].")
    if not isinstance(population_size, int) or not (5 <= population_size <= 20):
        raise ValueError("population_size must be an int in [5, 20].")
    if not isinstance(mutation_rate, float) or not (0.0 <= mutation_rate <= 1.0):
        raise ValueError("mutation_rate must be a float in [0.0, 1.0].")
    if (not isinstance(bounds, tuple) or len(bounds) != 2 or
        not all(isinstance(b, float) for b in bounds) or bounds[0] > bounds[1]):
        raise ValueError("bounds must be a (float, float) tuple with bounds[0] <= bounds[1].")

    np.random.seed(42)  # Required reproducibility

    min_val, max_val = bounds
    fixed = min_val == max_val

    # Start with random population or fixed values
    if fixed:
        population = np.full((population_size, pulse_length), min_val)
    else:
        population = np.random.uniform(min_val, max_val, (population_size, pulse_length))

    best_sequence = None
    best_fidelity = 0.0

    for gen in range(generations):
        fitness_scores = np.zeros(population_size)

        for i in range(population_size):
            final_state = simulate_pulse(population[i], initial_state, hamiltonian, pulse_length)
            fitness_scores[i] = fidelity(final_state, target_state)

        best_idx = int(np.argmax(fitness_scores))
        current_best = fitness_scores[best_idx]

        if current_best > best_fidelity:
            best_fidelity = current_best
            best_sequence = population[best_idx].copy()

        if gen == 0 and best_sequence is None:
            best_sequence = population[best_idx].copy()
            best_fidelity = current_best


        if generations == 1:
            break

        # Selection: keep top 50% based on fitness
        sorted_indices = np.argsort(fitness_scores)[::-1]
        selected = population[sorted_indices[:population_size // 2]]

        new_population = [seq.copy() for seq in selected]  # Elitism: preserve top sequences

        # Fill remaining slots via crossover + mutation
        while len(new_population) < population_size:
            parent1_idx = np.random.randint(0, len(selected))
            parent2_idx = parent1_idx
            while parent2_idx == parent1_idx:
                parent2_idx = np.random.randint(0, len(selected))

            parent1 = selected[parent1_idx]
            parent2 = selected[parent2_idx]

            if fixed:
                child = parent1.copy()
            else:
                # One-point crossover
                point = np.random.randint(1, pulse_length)
                child = np.empty(pulse_length)
                child[:point] = parent1[:point]
                child[point:] = parent2[point:]

                # Mutation
                if mutation_rate > 0.0:
                    child = mutate_sequence(child, mutation_rate, bounds)


            new_population.append(child)

        population = np.array(new_population[:population_size])


    best_fidelity = round(min(1.0, max(0.0, best_fidelity)), 5)  # Clamp to [0.0, 1.0]


    return best_sequence, best_fidelity


def simulate_pulse(pulse_sequence: np.ndarray, initial_state: Qobj,
                   hamiltonian: Qobj, pulse_length: int) -> Qobj:
    """Simulate time evolution for given pulse sequence."""
    times = np.linspace(0, pulse_length, pulse_length + 1)

    def pulse_coeff(t, args):
        idx = int(np.floor(t))
        idx = min(idx, pulse_length - 1)
        return pulse_sequence[idx]

    H = [hamiltonian, pulse_coeff]
    result = mesolve(H, initial_state, times, [], [])
    return result.states[-1]


def mutate_sequence(sequence: np.ndarray, mutation_rate: float,
                    bounds: Tuple[float, float]) -> np.ndarray:
    """Apply uniform mutation within ±10% of value range."""
    min_val, max_val = bounds
    mutated = sequence.copy()
    noise_range = (max_val - min_val) * 0.1

    for i in range(len(sequence)):
        if np.random.random() < mutation_rate:
            noise = np.random.uniform(-noise_range, noise_range)
            mutated[i] = np.clip(mutated[i] + noise, min_val, max_val)


    return mutated
