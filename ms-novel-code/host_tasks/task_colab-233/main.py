"""Flask app that implements an in-memory CRUD REST API for items."""

from flask import Flask, request, jsonify

items = {}


def create_app() -> Flask:
    """Create and return the Flask application."""
    app = Flask(__name__)

    def validate_item_data(data, is_post=True):
        """
        Validate the structure and content of item data.

        The 'is_post' flag determines if the validation is for a
        creation (POST) or update (PUT) request.
        """
        if not isinstance(data, dict):
            return False, "Request body must be a JSON object."

        if is_post:
            if (
                "id" not in data
                or "name" not in data
                or "value" not in data
            ):
                return (
                    False,
                    "Missing required fields: 'id', 'name', 'value'."
                )

            if not isinstance(data["id"], int):
                return False, "ID must be an integer."
            if data["id"] <= 0:
                return False, "ID must be a positive integer."
            if data["id"] in items:
                return (
                    False,
                    f"Item with ID {data['id']} already exists."
                )
            if (
                not isinstance(data["name"], str)
                or not data["name"]
                or len(data["name"]) > 100
            ):
                return (
                    False,
                    "Name must be a non-empty string and max 100 characters."
                )
            if (
                not isinstance(data["value"], float)
                or data["value"] <= 0
            ):
                return False, "Value must be a positive float."
        else:
            if not any(field in data for field in ["name", "value"]):
                return (
                    False,
                    "At least 'name' or 'value' must be provided for update."
                )

            if "name" in data:
                if (
                    not isinstance(data["name"], str)
                    or not data["name"]
                    or len(data["name"]) > 100
                ):
                    return (
                        False,
                        "Name must be a non-empty string and "
                        "max 100 characters."
                    )
            if "value" in data:
                if (
                    not isinstance(data["value"], float)
                    or data["value"] <= 0
                ):
                    return False, "Value must be a positive float."

        return True, None

    @app.route("/items", methods=["POST"])
    def create_item():
        """Create a new item."""
        data = request.get_json()
        if data is None:
            return jsonify({"message": "Request body must be JSON."}), 400

        is_valid, error_message = validate_item_data(data, is_post=True)
        if not is_valid:
            return jsonify({"message": error_message}), 400

        item = {
            "id": data["id"],
            "name": data["name"],
            "value": float(data["value"])
        }
        items[item["id"]] = item
        return jsonify(item), 201

    @app.route("/items", methods=["GET"])
    def get_all_items():
        """Return a list of all items."""
        return jsonify(list(items.values())), 200

    @app.route("/items/<int:item_id>", methods=["GET"])
    def get_item(item_id):
        """Return a single item by ID."""
        item = items.get(item_id)
        if item is None:
            return (
                jsonify({"message": f"Item with ID {item_id} not found."}),
                404
            )
        return jsonify(item), 200

    @app.route("/items/<int:item_id>", methods=["PUT"])
    def update_item(item_id):
        """Update an existing item by ID."""
        item = items.get(item_id)
        if item is None:
            return (
                jsonify({"message": f"Item with ID {item_id} not found."}),
                404
            )

        data = request.get_json()
        if data is None:
            return jsonify({"message": "Request body must be JSON."}), 400

        is_valid, error_message = validate_item_data(data, is_post=False)
        if not is_valid:
            return jsonify({"message": error_message}), 400

        if "name" in data:
            item["name"] = data["name"]
        if "value" in data:
            item["value"] = float(data["value"])

        items[item_id] = item
        return jsonify(item), 200

    @app.route("/items/<int:item_id>", methods=["DELETE"])
    def delete_item(item_id):
        """Delete an item by ID."""
        if item_id not in items:
            return (
                jsonify({"message": f"Item with ID {item_id} not found."}),
                404
            )

        del items[item_id]
        return jsonify({"message": "Item deleted"}), 200

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)

