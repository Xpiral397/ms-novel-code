
import os
import json
import uuid
import threading
import logging
import datetime
from typing import Any, Dict, List

import graphene
from flask import Flask
from flask_graphql import GraphQLView

USERS_FILE_PATH = os.environ.get('USERS_JSON_PATH', 'users.json')
_FILE_LOCK = threading.Lock()
_CACHE_TTL_SECONDS = 5
_cache: Dict[str, Any] = {'users': [], 'timestamp': None}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _atomic_write(path: str, data: str) -> None:
    """Atomically write data to a file."""
    temp_path = f"{path}.{uuid.uuid4().hex}.tmp"
    with open(temp_path, 'w', encoding='utf-8') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp_path, path)


def load_users(force_reload: bool = False) -> List[Dict[str, Any]]:
    now = datetime.datetime.utcnow()
    if (not force_reload and _cache['timestamp'] and
            (now - _cache['timestamp']).total_seconds() < _CACHE_TTL_SECONDS):
        return _cache['users']
    with _FILE_LOCK:
        if not os.path.exists(USERS_FILE_PATH):
            _atomic_write(USERS_FILE_PATH, '[]')
        with open(USERS_FILE_PATH, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                logger.warning("Corrupted JSON, resetting list.")
                data = []
        _cache['users'] = data
        _cache['timestamp'] = now
    return data


def save_users(users: List[Dict[str, Any]]) -> None:
    serialized = json.dumps(users, indent=2, default=str)
    with _FILE_LOCK:
        _atomic_write(USERS_FILE_PATH, serialized)
        _cache['timestamp'] = None


def find_user_index(user_list: List[Dict[str, Any]], user_id: str) -> int:
    for idx, u in enumerate(user_list):
        if u.get('id') == user_id:
            return idx
    return -1


def levenshtein(a: str, b: str) -> int:
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,
                dp[i][j - 1] + 1,
                dp[i - 1][j - 1] + cost
            )
    return dp[m][n]


class JSONOnlyGraphQLView(GraphQLView):
    def parse_body(self, request):
        if (not request.content_type or
                'application/json' not in request.content_type):
            raise ValueError(
                "Only 'application/json' supported."
            )
        return super().parse_body(request)


class UserType(graphene.ObjectType):
    id = graphene.ID(required=True)
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    created_at = graphene.String()
    updated_at = graphene.String()


class UserInput(graphene.InputObjectType):
    id = graphene.ID()
    name = graphene.String(required=True)
    email = graphene.String(required=True)


class Query(graphene.ObjectType):
    all_users = graphene.List(
        UserType,
        limit=graphene.Int(),
        offset=graphene.Int(),
        search=graphene.String(),
        fuzzy=graphene.String(),
        max_distance=graphene.Int()
    )
    user_by_id = graphene.Field(UserType, id=graphene.ID(required=True))

    def resolve_all_users(self, info, limit=None, offset=None,
                          search=None, fuzzy=None, max_distance=2):
        users = load_users()
        if fuzzy:
            key = fuzzy.lower()
            users = [
                u for u in users
                if levenshtein(key, u['name'].lower()) <= max_distance
                or levenshtein(key, u['email'].lower()) <= max_distance
            ]
        elif search:
            term = search.lower()
            users = [
                u for u in users
                if term in u['name'].lower()
                or term in u['email'].lower()
            ]
        start = offset or 0
        end = start + limit if limit else None
        return [UserType(**u) for u in users[start:end]]

    def resolve_user_by_id(self, info, id: str):
        users = load_users()
        idx = find_user_index(users, id)
        return UserType(**users[idx]) if idx != -1 else None


class CreateUser(graphene.Mutation):
    class Arguments:
        user_data = UserInput(required=True)
    ok = graphene.Boolean()
    user = graphene.Field(UserType)
    message = graphene.String()

    def mutate(self, info, user_data):
        users = load_users(force_reload=True)
        if any(u['email'].lower() == user_data.email.lower()
               for u in users):
            return CreateUser(ok=False, message="Email exists.")
        now = datetime.datetime.utcnow().isoformat()
        new_user = {
            'id': str(uuid.uuid4()),
            'name': user_data.name.strip(),
            'email': user_data.email.strip(),
            'created_at': now,
            'updated_at': now
        }
        users.append(new_user)
        save_users(users)
        return CreateUser(ok=True, user=UserType(**new_user),
                          message="User created.")


class UpdateUser(graphene.Mutation):
    class Arguments:
        user_data = UserInput(required=True)
    ok = graphene.Boolean()
    user = graphene.Field(UserType)
    message = graphene.String()

    def mutate(self, info, user_data):
        users = load_users(force_reload=True)
        idx = find_user_index(users, user_data.id)
        if idx == -1:
            return UpdateUser(ok=False, message="Not found.")
        if any(u['email'].lower() == user_data.email.lower()
               and u['id'] != user_data.id for u in users):
            return UpdateUser(ok=False, message="Email in use.")
        now = datetime.datetime.utcnow().isoformat()
        users[idx].update({
            'name': user_data.name.strip(),
            'email': user_data.email.strip(),
            'updated_at': now
        })
        save_users(users)
        return UpdateUser(ok=True, user=UserType(**users[idx]),
                          message="User updated.")


class DeleteUser(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
    ok = graphene.Boolean()
    message = graphene.String()

    def mutate(self, info, id):
        users = load_users(force_reload=True)
        idx = find_user_index(users, id)
        if idx == -1:
            return DeleteUser(ok=False, message="Not found.")
        deleted = users.pop(idx)
        save_users(users)
        return DeleteUser(ok=True, message=f"Deleted {deleted['name']}")


class BulkUpdateEmails(graphene.Mutation):
    class Arguments:
        updates = graphene.List(UserInput, required=True)
    ok = graphene.Boolean()
    updated_count = graphene.Int()
    failed = graphene.List(graphene.String)

    def mutate(self, info, updates):
        users = load_users(force_reload=True)
        failed_list: List[str] = []
        count = 0
        for inp in updates:
            idx = find_user_index(users, inp.id)
            if idx == -1:
                failed_list.append(f"{inp.id} not found")
                continue
            users[idx]['email'] = inp.email.strip()
            users[idx]['updated_at'] = (
                datetime.datetime.utcnow().isoformat()
            )
            count += 1
        save_users(users)
        return BulkUpdateEmails(ok=True, updated_count=count,
                                 failed=failed_list)


def logging_middleware(next_, root, info, **args):
    logger.info(f"GraphQL {info.field_name}, args={args}")
    try:
        return next_(root, info, **args)
    except Exception as e:
        logger.error(f"Error in {info.field_name}: {e}")
        raise


app = Flask(__name__)
schema = graphene.Schema(
    query=Query,
    mutation=graphene.ObjectType(
        create_user=CreateUser.Field(),
        update_user=UpdateUser.Field(),
        delete_user=DeleteUser.Field(),
        bulk_update_emails=BulkUpdateEmails.Field()
    )
)
app.add_url_rule(
    '/graphql',
    view_func=JSONOnlyGraphQLView.as_view(
        'graphql', schema=schema, graphiql=True,
        middleware=[logging_middleware]
    )
)

@app.route('/health', methods=['GET'])
def health_check():
    return {'status': 'ok',
            'timestamp': datetime.datetime.utcnow().isoformat()}


def start_file_watcher(interval_seconds: int = 10) -> None:
    def _watch():
        last_mod = (os.path.getmtime(USERS_FILE_PATH)
                    if os.path.exists(USERS_FILE_PATH) else None)
        while True:
            try:
                if os.path.exists(USERS_FILE_PATH):
                    new_mod = os.path.getmtime(USERS_FILE_PATH)
                    if last_mod and new_mod != last_mod:
                        logger.info("Cache invalidated.")
                        _cache['timestamp'] = None
                        last_mod = new_mod
                threading.Event().wait(interval_seconds)
            except Exception as e:
                logger.error(f"Watcher error: {e}")
                break
    watcher = threading.Thread(target=_watch, daemon=True)
    watcher.start()


if __name__ == '__main__':
    if not os.path.exists(USERS_FILE_PATH):
        _atomic_write(USERS_FILE_PATH, '[]')
    start_file_watcher()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

