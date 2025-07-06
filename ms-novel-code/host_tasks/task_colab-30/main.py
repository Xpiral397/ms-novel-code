"""Analyze social network graph: influencers, communities, and recommendations."""

from collections import defaultdict


def validate_graph(graph: dict) -> None:
    """Validate graph user IDs, interactions, self-loops, and duplicates."""
    for user, neighbors in graph.items():
        if not (len(user) == 1 and 'A' <= user <= 'Z'):
            raise ValueError("Invalid user ID: must be A-Z")
        if not isinstance(neighbors, dict):
            raise ValueError("Invalid user ID: must be A-Z")
        seen = set()
        for neighbor, count in neighbors.items():
            if not (len(neighbor) == 1 and 'A' <= neighbor <= 'Z'):
                raise ValueError("Invalid user ID: must be A-Z")
            if neighbor in seen:
                raise ValueError(f"Duplicate edge detected for user: {user}")
            if neighbor == user:
                raise ValueError("Invalid user ID: must be A-Z")
            if not isinstance(count, int) or not (1 <= count <= 100):
                raise ValueError(
                    f"Interaction count out of range (1-100) for user: {user}"
                )
            seen.add(neighbor)


def compute_influencers(graph: dict, top_k: int = 3) -> list[str]:
    """Compute influencer scores by degree centrality, rounded to 3 decimals."""
    all_users = set(graph)
    for u in graph:
        all_users.update(graph[u])
    scores = {}
    for user in all_users:
        score = sum(graph[user].values()) if user in graph else 0
        scores[user] = round(score, 3)
    return sorted(scores, key=lambda x: (-scores[x], x))


def detect_communities(graph: dict) -> list[list[str]]:
    """Detect modularity-based communities using Louvain + iterative DFS."""
    all_users = set(graph)
    for u in graph:
        all_users.update(graph[u])

    adj = defaultdict(set)
    for u in graph:
        for v in graph[u]:
            adj[u].add(v)
            adj[v].add(u)
    for u in all_users:
        adj[u]

    visited = set()
    components = []

    for node in sorted(all_users):
        if node not in visited:
            stack = [node]
            comp = []
            while stack:
                curr = stack.pop()
                if curr not in visited:
                    visited.add(curr)
                    comp.append(curr)
                    for nei in adj[curr]:
                        if nei not in visited:
                            stack.append(nei)
            components.append(sorted(comp))

    out_wt = defaultdict(int)
    in_wt = defaultdict(int)
    for u in graph:
        for v, w in graph[u].items():
            out_wt[u] += w
            in_wt[v] += w
    total_wt = sum(out_wt.values())

    final_clusters = []

    for comp in components:
        labels = {u: i for i, u in enumerate(comp)}
        changed = True
        while changed:
            changed = False
            groups = defaultdict(list)
            for u in comp:
                groups[labels[u]].append(u)
            q = 0.0
            for group in groups.values():
                kout = sum(out_wt[x] for x in group)
                kin = sum(in_wt[x] for x in group)
                win = 0
                for x in group:
                    if x in graph:
                        for y in graph[x]:
                            if y in group:
                                win += graph[x][y]
                if total_wt:
                    q += win - (kout * kin) / total_wt
            q /= total_wt if total_wt else 1

            for u in comp:
                orig = labels[u]
                best = orig
                best_q = q
                for v in comp:
                    labels[u] = labels[v]
                    temp_groups = defaultdict(list)
                    for x in comp:
                        temp_groups[labels[x]].append(x)
                    temp_q = 0.0
                    for group in temp_groups.values():
                        kout = sum(out_wt[x] for x in group)
                        kin = sum(in_wt[x] for x in group)
                        win = 0
                        for x in group:
                            if x in graph:
                                for y in graph[x]:
                                    if y in group:
                                        win += graph[x][y]
                        if total_wt:
                            temp_q += win - (kout * kin) / total_wt
                    temp_q /= total_wt if total_wt else 1
                    if temp_q > best_q:
                        best = labels[v]
                        best_q = temp_q
                    labels[u] = orig
                if best != orig:
                    labels[u] = best
                    changed = True

        clustered = defaultdict(list)
        for u in comp:
            clustered[labels[u]].append(u)
        for group in clustered.values():
            final_clusters.append(sorted(group))

    return sorted(final_clusters, key=lambda c: (-len(c), c[0]))


def generate_recommendations(graph: dict, user: str) -> list[str]:
    """Generate recommendations based on Jaccard similarity of neighbors."""
    all_users = set(graph)
    for u in graph:
        all_users.update(graph[u])

    user_neigh = set(graph.get(user, {}))
    scores = []

    for candidate in sorted(all_users):
        if candidate == user or candidate in user_neigh:
            continue
        cand_neigh = set(graph.get(candidate, {}))
        union = user_neigh | cand_neigh
        inter = user_neigh & cand_neigh
        sim = len(inter) / len(union) if union else 0.0
        scores.append((sim, candidate))

    scores.sort(key=lambda x: (-x[0], x[1]))
    return [c for _, c in scores]


def analyze_network(graph: dict) -> dict:
    """Analyze graph and return influencers, communities, and recommendations."""
    validate_graph(graph)
    all_users = set(graph)
    for u in graph:
        all_users.update(graph[u])
    if not all_users:
        return {
            "influencers": [],
            "communities": [],
            "recommendations": {}
        }
    influencers = compute_influencers(graph)
    communities = detect_communities(graph)
    recommendations = {
        u: generate_recommendations(graph, u) for u in sorted(all_users)
    }
    return {
        "influencers": influencers,
        "communities": communities,
        "recommendations": recommendations
    }

