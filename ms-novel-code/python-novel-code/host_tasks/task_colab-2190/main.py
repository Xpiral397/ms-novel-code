
"""Priority queue task scheduler implementation."""

import heapq
from typing import List, Union


def task_scheduler(
    operations: List[List[Union[str, int]]]
) -> List[Union[str, List]]:
    """
    Implement a priority-based task scheduler using heapq.

    Args:
        operations: List of operations to perform on the scheduler

    Returns:
        List of responses for each operation
    """
    heap = []
    arrival_order = 0
    job_registry = {}
    results = []

    for operation in operations:
        op_type = operation[0]

        if op_type == "add":
            _, job_id, priority, execution_time = operation

            if job_id in job_registry:
                results.append(f"Error: Job {job_id} already exists")
            else:
                heapq.heappush(
                    heap, (priority, arrival_order, job_id, execution_time)
                )
                job_registry[job_id] = True
                arrival_order += 1
                results.append(f"Job {job_id} added")

        elif op_type == "execute":
            time_units = operation[1]
            completed_jobs = []
            remaining_time = time_units

            if time_units == 0:
                results.append([])
                continue

            jobs_in_progress = {}

            while heap and remaining_time > 0:
                priority, order, job_id, job_time = heapq.heappop(heap)

                time_spent = min(remaining_time, job_time)
                remaining_time -= time_spent
                job_time -= time_spent

                if job_id in jobs_in_progress:
                    jobs_in_progress[job_id] += time_spent
                else:
                    jobs_in_progress[job_id] = time_spent

                if job_time > 0:
                    heapq.heappush(heap, (priority, order, job_id, job_time))
                else:
                    completed_jobs.append([job_id, jobs_in_progress[job_id]])
                    del job_registry[job_id]

            results.append(completed_jobs)

        elif op_type == "status":
            queue_status = []
            temp_heap = []

            while heap:
                priority, order, job_id, remaining = heapq.heappop(heap)
                queue_status.append([job_id, priority, remaining])
                temp_heap.append((priority, order, job_id, remaining))

            for item in temp_heap:
                heapq.heappush(heap, item)

            results.append(queue_status)

    return results

