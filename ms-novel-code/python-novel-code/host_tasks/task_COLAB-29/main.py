
def max_active_students(intervals: dict[int, list[list[int]]],
                        dependencies: dict[tuple[int, int], list[tuple[int, int]]],
                        query_times: list[int]) -> int:

    # Performing input validation and checking for edge cases
    try:
        if not isinstance(intervals, dict) or not isinstance(dependencies, dict) or not isinstance(query_times, list):
            return 0
        if not intervals or not query_times:
            return 0
        for student_id, student_intervals in intervals.items():
            if not isinstance(student_id, int) or not isinstance(student_intervals, list):
                return 0
            for interval in student_intervals:
                if (not isinstance(interval, list) or len(interval) != 2 or
                    not all(isinstance(x, int) and x >= 0 for x in interval) or
                    interval[0] > interval[1]):
                    return 0
        for interval_key, prereqs in dependencies.items():
            if (not isinstance(interval_key, tuple) or len(interval_key) != 2 or
                not isinstance(prereqs, list)):
                return 0
            for prereq in prereqs:
                if not isinstance(prereq, tuple) or len(prereq) != 2:
                    return 0
        for time in query_times:
            if not isinstance(time, int) or time < 0:
                return 0
    except:
        return 0

    # Step 1: Assigning unique IDs to all intervals
    interval_id_map = {}  # Maps (student_id, interval_index) to unique ID
    start_times = []
    end_times = []
    student_owners = []
    current_id = 0

    for student_id, student_intervals in intervals.items():
        for idx, (start, end) in enumerate(student_intervals):
            interval_id_map[(student_id, idx)] = current_id
            start_times.append(start)
            end_times.append(end)
            student_owners.append(student_id)
            current_id += 1

    total_intervals = current_id

    # Validating that all dependency references are valid
    for target_interval, prereq_list in dependencies.items():
        if target_interval not in interval_id_map:
            return 0
        for prereq_interval in prereq_list:
            if prereq_interval not in interval_id_map:
                return 0

    # Step 2: Build graph and compute indegrees for topological sort
    graph = [[] for _ in range(total_intervals)]
    indegree = [0] * total_intervals

    for target, prereq_list in dependencies.items():
        target_id = interval_id_map[target]
        for prereq in prereq_list:
            prereq_id = interval_id_map[prereq]
            graph[prereq_id].append(target_id)
            indegree[target_id] += 1

    # Step 3: Doing topological sort using queue (manual)
    topo_queue = []
    for i in range(total_intervals):
        if indegree[i] == 0:
            topo_queue.append(i)

    topo_order = []
    head = 0
    while head < len(topo_queue):
        current = topo_queue[head]
        head += 1
        topo_order.append(current)
        for neighbor in graph[current]:
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                topo_queue.append(neighbor)

    # If not all intervals are sorted, there's a cycle
    if len(topo_order) < total_intervals:
        return 0

    # Step 4: Computing earliest valid start time after dependencies are met
    latest_dependency_end = [0] * total_intervals
    for interval in topo_order:
        for neighbor in graph[interval]:
            latest_dependency_end[neighbor] = max(latest_dependency_end[neighbor], end_times[interval])

    # Step 5: Building per-student list of valid (active) intervals
    student_valid_intervals = {}
    for (student_id, interval_idx), internal_id in interval_id_map.items():
        effective_start = max(start_times[internal_id], latest_dependency_end[internal_id])
        effective_end = end_times[internal_id]
        if effective_start <= effective_end:
            if student_id not in student_valid_intervals:
                student_valid_intervals[student_id] = []
            student_valid_intervals[student_id].append([effective_start, effective_end])

    # Step 6: Merging intervals for each student (per student only counts once)
    all_merged_intervals = []
    for intervals_list in student_valid_intervals.values():
        intervals_list.sort()
        merged_start, merged_end = intervals_list[0]
        for start, end in intervals_list[1:]:
            if start <= merged_end + 1:
                merged_end = max(merged_end, end)
            else:
                all_merged_intervals.append((merged_start, merged_end))
                merged_start, merged_end = start, end
        all_merged_intervals.append((merged_start, merged_end))

    if not all_merged_intervals:
        return 0

    # Step 7: Preparing sweep line events
    events = []
    for start, end in all_merged_intervals:
        events.append((start, 1))      # Student becomes active
        events.append((end + 1, -1))   # Student becomes inactive

    events.sort()

    # Step 8: Processing all queries to count active students
    queries = [(time, idx) for idx, time in enumerate(query_times)]
    queries.sort()

    active_students = 0
    result = [0] * len(query_times)
    event_ptr = 0

    for query_time, original_idx in queries:
        while event_ptr < len(events) and events[event_ptr][0] <= query_time:
            active_students += events[event_ptr][1]
            event_ptr += 1
        result[original_idx] = active_students

    return max(result)
