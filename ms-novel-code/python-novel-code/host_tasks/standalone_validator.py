#!/usr/bin/env python3
"""
Standalone Novel Code Task Validator

A standalone tool for validating Novel Code tasks using local .ipynb files.
No external dependencies required - pure Python!

Example usage:
uv run python scripts/standalone_validator.py \
    --container-id ms-novel-code-sandbox \
    --container-tool podman \
    --tasks-dir ../tasks \
    --clean \
    ../colabs/working.ipynb
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# === Container Management ===

class ContainerTool(str, Enum):
    """Container management tool to use."""
    PODMAN = "podman"
    DOCKER = "docker"
    ENROOT = "enroot"


class ContainerExecutor:
    """Executes commands within a specified, running Docker, Podman, or Enroot container."""

    def __init__(self, container_id: str, tool: Optional[ContainerTool] = None, enroot_mounts: Optional[List[str]] = None):
        """Initialize the executor."""
        self.tool = tool or self._detect_container_tool()
        if not self.tool:
            raise RuntimeError("None of 'podman', 'docker', or 'enroot' command found in PATH.")

        if not shutil.which(self.tool.value):
            raise FileNotFoundError(f"Container tool '{self.tool.value}' not found in PATH.")

        if self.tool == ContainerTool.ENROOT:
            self.container_id = container_id
            self.enroot_mounts = enroot_mounts or []
            if not self._enroot_container_exists(container_id):
                raise RuntimeError(f"Enroot container '{container_id}' not found.")
        else:
            self.container_id = self._resolve_container_id(container_id)
            self.enroot_mounts = []
            if not self.container_id:
                raise RuntimeError(f"Container '{container_id}' not found or not running.")

    def _detect_container_tool(self) -> Optional[ContainerTool]:
        """Detects available container tool (podman has priority, then docker, then enroot)."""
        if shutil.which(ContainerTool.PODMAN):
            return ContainerTool.PODMAN
        elif shutil.which(ContainerTool.DOCKER):
            return ContainerTool.DOCKER
        elif shutil.which(ContainerTool.ENROOT):
            return ContainerTool.ENROOT
        else:
            return None

    def _run_container_command(self, command: List[str], **kwargs) -> subprocess.CompletedProcess:
        """Helper to run a command using the selected container tool."""
        base_command = [self.tool.value] + command
        try:
            return subprocess.run(
                base_command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
                **kwargs,
            )
        except FileNotFoundError:
            raise FileNotFoundError(f"Container tool '{self.tool.value}' not found when trying to execute {command}")
        except Exception as e:
            raise RuntimeError(f"Error running container command '{' '.join(base_command)}': {e}") from e

    def _list_containers(self) -> List[Dict]:
        """Lists running containers using the selected tool."""
        if self.tool == ContainerTool.ENROOT:
            return []

        format_option = "json"
        cmd = ["ps", "--format", format_option]
        if self.tool == ContainerTool.DOCKER:
            cmd.insert(1, "--no-trunc")

        result = self._run_container_command(cmd)
        if result.returncode != 0:
            print(f"Failed to list containers: {result.stderr}", file=sys.stderr)
            return []

        try:
            stdout = result.stdout.strip()
            if not stdout:
                return []

            if self.tool == ContainerTool.DOCKER and "\n" in stdout:
                containers_raw = [json.loads(line) for line in stdout.splitlines()]
            else:
                containers_raw = json.loads(stdout)
                if not isinstance(containers_raw, list):
                    containers_raw = [containers_raw]

            processed = []
            for c in containers_raw:
                processed.append({
                    "Id": c.get("ID") or c.get("Id"),
                    "Names": c.get("Names"),
                    "Image": c.get("Image"),
                    "Status": c.get("State") or c.get("Status"),
                })
            return processed
        except json.JSONDecodeError as e:
            print(f"Failed to parse container list JSON: {e}", file=sys.stderr)
            return []
        except Exception as e:
            print(f"Unexpected error processing container list: {e}", file=sys.stderr)
            return []

    def _resolve_container_id(self, container_name_or_id: str) -> Optional[str]:
        """Finds the full container ID from a name or partial/full ID."""
        containers = self._list_containers()
        if not containers:
            return None

        for container in containers:
            container_id = container.get("Id")
            if container_id and container_id.startswith(container_name_or_id):
                return container_id

        for container in containers:
            names = container.get("Names", [])
            if isinstance(names, str):
                names = names.split(",")
            if container_name_or_id in names:
                return container.get("Id")

        return None

    def _enroot_container_exists(self, container_name: str) -> bool:
        """Checks if an Enroot container exists."""
        try:
            result = self._run_container_command(["list"])
            if result.returncode != 0:
                return False

            for line in result.stdout.strip().split('\n'):
                if line.strip() == container_name:
                    return True
            return False
        except Exception:
            return False

    def execute(self, command: List[str], workdir: Optional[str] = None, env: Optional[Dict[str, str]] = None) -> Tuple[int, str, str]:
        """Execute a command within the container."""
        if self.tool == ContainerTool.ENROOT:
            return self._execute_enroot(command, workdir, env)
        else:
            return self._execute_podman_docker(command, workdir, env)

    def _execute_enroot(self, command: List[str], workdir: Optional[str] = None, env: Optional[Dict[str, str]] = None) -> Tuple[int, str, str]:
        """Execute command using Enroot."""
        enroot_cmd = ["exec"]

        for mount in self.enroot_mounts:
            enroot_cmd.extend(["-m", mount])

        if env:
            for key, value in env.items():
                enroot_cmd.extend(["-e", f"{key}={value}"])

        enroot_cmd.append(self.container_id)

        if workdir:
            bash_cmd = f"cd {workdir} && {' '.join(command)}"
            enroot_cmd.extend(["bash", "-c", bash_cmd])
        else:
            enroot_cmd.extend(command)

        result = self._run_container_command(enroot_cmd)
        return result.returncode, result.stdout, result.stderr

    def _execute_podman_docker(self, command: List[str], workdir: Optional[str] = None, env: Optional[Dict[str, str]] = None) -> Tuple[int, str, str]:
        """Execute command using Podman or Docker."""
        exec_cmd = ["exec"]

        if env:
            for key, value in env.items():
                exec_cmd.extend(["-e", f"{key}={value}"])

        if workdir:
            exec_cmd.extend(["-w", workdir])

        exec_cmd.append(self.container_id)
        exec_cmd.extend(command)

        result = self._run_container_command(exec_cmd)
        return result.returncode, result.stdout, result.stderr


# === Helper Functions ===

def load_local_notebook(file_path: str) -> dict:
    """Loads a local Jupyter/Colab notebook file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        raise FileNotFoundError(f"Notebook file not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in notebook file {file_path}: {e}")
    except Exception as e:
        raise RuntimeError(f"Error reading notebook file {file_path}: {e}")


def extract_id_from_path(file_path: str) -> str:
    """Extract a unique identifier from the file path for task folder naming."""
    path_obj = Path(file_path)
    return path_obj.stem


def extract_metadata_dict(strings: List[str]) -> Dict[str, str]:
    """Extracts key-value pairs from lines like **Key**: Value."""
    import re
    result = {}
    for s in strings:
        match = re.match(r"\*\*(.*?)\*\*[:\s]*(.*)", s)
        if match:
            key, value = match.groups()
            key = key.strip("-").strip()
            value = value.strip().strip("-").strip()
            if key:
                result[key] = value
    return result


def parse_test_code(cell_source: List[str]) -> str:
    """Parses test code from cell source, preserving original content."""
    code_block = ''.join(cell_source)
    return code_block.strip()


def extract_requirements_from_setup(setup_content: Optional[str]) -> List[str]:
    """Extracts package names from a ```requirements.txt block within setup content."""
    import re
    if not setup_content or not isinstance(setup_content, str):
        return []

    req_pattern = re.compile(r"```requirements\.txt\n(.*?)```", re.DOTALL | re.IGNORECASE)
    match = req_pattern.search(setup_content)

    if not match:
        return []

    requirements_str = match.group(1).strip()
    if not requirements_str:
        return []

    requirements = [
        line.strip()
        for line in requirements_str.splitlines()
        if line.strip() and not line.strip().startswith('#')
    ]
    return requirements


def find_closest_match(input_string: str) -> str:
    """Finds the closest header name match using fuzzy matching (simplified version)."""
    # Simplified fuzzy matching - convert to lowercase and check for key terms
    input_lower = input_string.lower()

    # Define header mappings (similar to core.py's HEADER_NAMES)
    if 'prompt' in input_lower:
        return 'prompt'
    elif 'code' in input_lower:
        return 'code'
    elif any(term in input_lower for term in ['test', 'unit test', 'unit tests']):
        return 'tests'
    elif 'requirement' in input_lower:
        return 'requirements'
    elif 'setup' in input_lower:
        return 'setup'
    else:
        return input_lower  # Return as-is if no match


def get_today_date_str() -> str:
    """Returns the current date as YYYYMMDD."""
    return datetime.now().strftime("%Y%m%d")


def calculate_content_hash(colab_data: dict) -> str:
    """Calculate SHA256 hash of colab content for change detection."""
    content_parts = []

    if 'cells' in colab_data:
        for cell in colab_data['cells']:
            if isinstance(cell, dict) and 'source' in cell:
                if isinstance(cell['source'], list):
                    source_content = ''.join(cell['source'])
                else:
                    source_content = str(cell['source'])
                content_parts.append(source_content)

    full_content = '\n'.join(content_parts)
    return hashlib.sha256(full_content.encode('utf-8')).hexdigest()


def normalize_taxonomy_fields(metadata: dict) -> dict:
    """Normalize taxonomy fields in metadata to ensure consistent L1 and L2 taxonomy format."""
    if not isinstance(metadata, dict):
        return metadata

    normalized_metadata = metadata.copy()

    if "Taxonomy" in normalized_metadata:
        taxonomy_value = normalized_metadata["Taxonomy"]

        if isinstance(taxonomy_value, str) and " > " in taxonomy_value:
            parts = taxonomy_value.split(" > ", 1)
            if len(parts) == 2:
                l1_taxonomy = parts[0].strip()
                l2_taxonomy = parts[1].strip()

                if "L1 Taxonomy" not in normalized_metadata:
                    normalized_metadata["L1 Taxonomy"] = l1_taxonomy
                if "L2 Taxonomy" not in normalized_metadata:
                    normalized_metadata["L2 Taxonomy"] = l2_taxonomy

                del normalized_metadata["Taxonomy"]

    return normalized_metadata


# === Core Processing Functions ===

def process_notebook_data(colab_data: dict, task_id: str) -> Optional[dict]:
    """Processes the downloaded JSON data from a single Colab notebook."""
    try:
        metadata_cell_source = colab_data["cells"][0]["source"]
    except (KeyError, IndexError, TypeError) as e:
        print(f"Warning: Could not extract metadata cell from notebook {task_id}. Error: {e}")
        return None

    metadata = extract_metadata_dict(metadata_cell_source)
    metadata = {key: val for key, val in metadata.items() if key.lower() != "use case"}
    metadata = normalize_taxonomy_fields(metadata)

    content_hash = calculate_content_hash(colab_data)
    today_date = get_today_date_str()

    json_item = {
        "idx": 1,
        "batch_idx": 1,
        "date": today_date,
        "question": None,
        "answer": None,
        "verification": None,
        "category": "code",
        "setup_instructions": None,
        "metadata": metadata,
        "colab_id": task_id,
        "colab_content_hash": content_hash,
    }

    requirements_content = None

    def is_code_cell_with_comment(cell: dict, comment: str) -> bool:
        """Check if a cell is a code cell with a specific comment as the first non-empty line."""
        if not isinstance(cell, dict):
            return False

        cell_type = cell.get("cell_type", "")
        if cell_type != "code":
            return False

        cell_source = cell.get("source", [])
        if not isinstance(cell_source, list):
            return False

        for line in cell_source:
            if isinstance(line, str):
                stripped_line = line.strip()
                if stripped_line:
                    # Case-insensitive matching
                    return stripped_line.lower().startswith(comment.lower())

        return False

    def extract_title_and_filter_mod(lst):
        """Alternative title extraction focusing on the first non-empty line (from core.py)."""
        if not lst:
            return None, None

        first_item_content = None
        first_item_index = -1
        for i, item in enumerate(lst):
            cleaned_item = item.replace('\n', '').replace('\t', '').replace('\r', '').strip()
            if cleaned_item:
                first_item_content = item
                first_item_index = i
                break

        if first_item_content is None:
            return None, ''.join(lst)  # Return empty joined string to preserve exact formatting

        # Join the remaining text with original formatting
        remaining_text = ''.join(lst[first_item_index + 1:])

        # Clean the extracted title
        first_item_title = first_item_content.replace('**', '').replace('#', '').strip().lower()
        return first_item_title, remaining_text

    def is_test_cell(cell: dict) -> bool:
        """Check if a cell contains test code based on cell type and content patterns."""
        if not isinstance(cell, dict):
            return False

        cell_type = cell.get("cell_type", "")
        if cell_type != "code":
            return False

        cell_source = cell.get("source", [])
        if not isinstance(cell_source, list):
            return False

        content = ''.join(cell_source).lower()
        test_patterns = ["test_cases", "def test_", "unittest", "assert", "# test"]

        return any(pattern in content for pattern in test_patterns)

    def extract_cell_content_without_first_line(cell_source: list) -> str:
        """Extract cell content without the first non-empty line (title/comment)."""
        if not isinstance(cell_source, list):
            return ""

        first_non_empty_idx = None
        for i, line in enumerate(cell_source):
            if isinstance(line, str) and line.strip():
                first_non_empty_idx = i
                break

        if first_non_empty_idx is None:
            return ''.join(cell_source)

        remaining_content = cell_source[first_non_empty_idx + 1:]
        return ''.join(remaining_content)

    # Process cells looking for specific patterns
    # Skip the first cell (metadata) and process all other cells - like core.py
    for i, cell in enumerate(colab_data.get("cells", [])[1:], 1):  # Start from cell 1, keep index for debug
        if not isinstance(cell, dict) or "source" not in cell:
            print(f"Warning: Skipping malformed cell in notebook data at index {i}.")
            continue

        cell_source = cell.get("source", [])
        if not isinstance(cell_source, list):
            print(f"Warning: Cell source is not a list in notebook data at index {i}. Skipping cell.")
            continue

        # Check if the cell is completely empty
        if not any(str(line).strip() for line in cell_source):
            continue

        # Debug: show what cell we're processing
        cell_type = cell.get("cell_type", "unknown")
        cell_preview = ''.join(cell_source)[:50].replace('\n', ' ')
        print(f"   Processing cell {i} ({cell_type}): {cell_preview}...")  # Debug output

        # Special handling for code cells with # code comment (like core.py)
        if is_code_cell_with_comment(cell, "# code") and not json_item["answer"]:
            print(f"   Found code cell with '# code' comment at index {i}")
            json_item["answer"] = extract_cell_content_without_first_line(cell_source)
            continue

        # Special handling for test cells based on content patterns (like core.py)
        if is_test_cell(cell) and not json_item["verification"]:
            print(f"   Found test cell based on content patterns at index {i}")
            json_item["verification"] = parse_test_code(cell_source)
            continue

        # For markdown cells and other cells, use the existing title-based approach (like core.py)
        cell_title, remaining_text = extract_title_and_filter_mod(cell_source)

        if not cell_title or remaining_text is None:  # Ensure both are valid
            continue

        # Skip specific unwanted titles (case-insensitive) - like core.py
        if "o1 code" in cell_title.lower():
            continue

        # Skip "model breaking hints" cells (case-insensitive) - like core.py
        if "model breaking hints" in cell_title.lower():
            continue

        # Find closest match among predefined headers - use original title for specific checks (like core.py)
        matched_title = find_closest_match(cell_title)

        # Assign based on cell title or matched title, only if field is not already filled
        # Prioritize exact title match for "Setup" (like core.py)
        if cell_title.lower() == "setup" and not json_item.get("setup_instructions"):
            json_item["setup_instructions"] = remaining_text
            print(f"   Found setup cell via title: {remaining_text[:100]}...")  # Debug output
        # Check for Requirements field (exact match, case-insensitive) (like core.py)
        elif cell_title.lower() == "requirements" and not requirements_content:
            requirements_content = remaining_text
            print(f"   Found requirements cell via title: {remaining_text[:100]}...")  # Debug output
        # Then check matched titles for other fields (like core.py)
        elif matched_title == "prompt" and not json_item.get("question"):
            json_item["question"] = remaining_text
            print(f"   Found prompt cell via fuzzy match: {remaining_text[:100]}...")  # Debug output
        elif matched_title == "code" and not json_item["answer"]:
            # Only use title-based matching for code if we haven't found it via cell type
            json_item["answer"] = remaining_text
            print(f"   Found code cell via fuzzy match: {remaining_text[:100]}...")  # Debug output
        elif (
            matched_title in ["tests", "unit test", "unit tests"]
            and not json_item.get("verification")
        ):
            # Use the dedicated parsing function for test code
            # We pass the original unfiltered cell source to preserve whitespace
            json_item["verification"] = parse_test_code(cell_source)
            print(f"   Found test cell via fuzzy match: {matched_title}")  # Debug output

    # Fallback mechanisms for missing critical content (like core.py)
    if not json_item["answer"]:
        # Look for any code cell as a fallback
        print("   No answer found via primary methods, looking for fallback code cell")
        for cell in colab_data.get("cells", [])[1:]:
            if (isinstance(cell, dict) and
                cell.get("cell_type") == "code" and
                isinstance(cell.get("source"), list) and
                any(str(line).strip() for line in cell.get("source", []))):

                # Skip if this looks like a test cell
                if not is_test_cell(cell):
                    print("   Using fallback code cell for answer")
                    json_item["answer"] = ''.join(cell.get("source", []))
                    break

    if not json_item["verification"]:
        # Look for any cell that might contain tests as a fallback
        print("   No verification found via primary methods, looking for fallback test content")
        for cell in colab_data.get("cells", [])[1:]:
            if (isinstance(cell, dict) and
                isinstance(cell.get("source"), list)):

                content = ''.join(cell.get("source", [])).lower()
                # More permissive test detection for fallback
                if any(pattern in content for pattern in ["test", "assert", "check"]) and len(content.strip()) > 10:
                    print("   Using fallback test content for verification")
                    json_item["verification"] = parse_test_code(cell.get("source", []))
                    break

    # Append requirements content to question if both exist (like core.py)
    if json_item.get("question") and requirements_content:
        json_item["question"] += "\n\n**Requirements**\n\n" + requirements_content
        print(f"   Appended requirements to question: {requirements_content[:100]}...")  # Debug output

    # Basic validation: Ensure essential fields are filled (like core.py)
    if not json_item.get("question") or not json_item.get("answer"):
        print(f"   Warning: Missing question or answer for notebook {task_id}. Skipping item.")
        return None

    # Final debug output
    if json_item.get("setup_instructions"):
        print(f"   Final setup_instructions: {json_item['setup_instructions'][:100]}...")  # Debug output
    else:
        print("   No setup_instructions set")  # Debug output

    if json_item.get("answer"):
        print(f"   Final answer (code): {json_item['answer'][:100]}...")  # Debug output
    else:
        print("   No answer (code) found")  # Debug output

    return json_item


def unpack_single_task(task_data: dict, output_dir: Path, task_folder_name: str, clean: bool = False) -> bool:
    """Unpacks a single task dictionary into a specified folder."""
    folder_path = output_dir / task_folder_name
    try:
        if clean and folder_path.exists():
            shutil.rmtree(folder_path)

        folder_path.mkdir(exist_ok=True, parents=True)

        answer = task_data.get('answer', '')
        verification = task_data.get('verification', '')
        setup_content = task_data.get('setup_instructions')

        # Write the files
        with open(folder_path / "main.py", 'w', encoding='utf-8') as main_file:
            main_file.write(str(answer) + '\n')

        with open(folder_path / "tests.py", 'w', encoding='utf-8') as tests_file:
            tests_file.write(str(verification) + '\n')

        # Handle requirements.txt
        requirements = extract_requirements_from_setup(setup_content)
        if requirements:
            with open(folder_path / "requirements.txt", 'w', encoding='utf-8') as req_file:
                req_file.write("\n".join(requirements) + "\n")

        return True

    except (IOError, OSError) as e:
        print(f"Error unpacking task to {folder_path}: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Unexpected error unpacking task to {folder_path}: {e}", file=sys.stderr)
        return False


# === Main Validation Function ===

def validate_notebook_tasks(
    notebook_files: List[str],
    container_id: str,
    container_tool: Optional[ContainerTool] = None,
    tasks_dir: str = "./tasks",
    runs: int = 10,
    clean: bool = True,
    verbose: bool = True,
):
    """Main function to validate local notebook tasks."""
    tasks_path = Path(tasks_dir).resolve()
    print(f"Using tasks folder: {tasks_path}")
    print(f"Processing local notebook files: {notebook_files}")

    # Ensure tasks directory exists
    tasks_path.mkdir(parents=True, exist_ok=True)

    # Initialize container executor
    enroot_mounts = None
    if container_tool == ContainerTool.ENROOT:
        enroot_mounts = [f"{tasks_path}:/tasks"]

    executor = ContainerExecutor(
        container_id=container_id, tool=container_tool, enroot_mounts=enroot_mounts
    )

    successful_tasks = []
    failed_tasks = []

    for notebook_file in notebook_files:
        print(f"\n{'=' * 60}")
        print(f"Processing Notebook File: {notebook_file}")
        print(f"{'=' * 60}")

        try:
            # Step 1: Load notebook data from local file
            print("1. Loading local notebook file...")
            colab_data = load_local_notebook(notebook_file)
            print("✓ Loaded local notebook data")
            # Extract ID from file path for folder naming
            task_id = extract_id_from_path(notebook_file)

            processed_data = process_notebook_data(colab_data, task_id)
            if not processed_data:
                print("❌ Failed to process notebook data")
                failed_tasks.append({
                    "notebook_file": notebook_file,
                    "step": "process_notebook",
                    "error": "Failed to process notebook data",
                })
                continue

            print("✓ Processed notebook data")

            # Step 2: Extract/unpack data to task folder
            print("2. Extracting data to task folder...")
            task_folder_name = f"task_{task_id}"

            success = unpack_single_task(
                task_data=processed_data,
                output_dir=tasks_path,
                task_folder_name=task_folder_name,
                clean=clean,
            )

            if not success:
                print("❌ Failed to unpack task data")
                failed_tasks.append({
                    "notebook_file": notebook_file,
                    "step": "unpack_data",
                    "error": "Failed to unpack task data to folder",
                })
                continue

            task_folder_path = tasks_path / task_folder_name
            print(f"✓ Unpacked to: {task_folder_path}")

            # Step 3: Run test_runner_script_ng.py
            print("3. Running tests...")
            container_task_path = f"/tasks/{task_folder_name}"

            # Copy test runner script to tasks folder if it doesn't exist
            test_script_path = tasks_path / "test_runner_script_ng.py"
            if not test_script_path.exists():
                # Look for test runner in the same directory as this script
                scripts_dir = Path(__file__).parent
                source_test_runner = scripts_dir / "test_runner_script_ng.py"
                if source_test_runner.exists():
                    shutil.copy2(source_test_runner, test_script_path)
                    print("✓ Copied test runner script to tasks folder")
                else:
                    print("⚠️  test_runner_script_ng.py not found in scripts directory")

            # Check if requirements exist and set up environment if needed
            ret, out, err = executor.execute(["test", "-f", f"{container_task_path}/requirements.txt"])
            python_executable = "python"

            if ret == 0:
                # Requirements file exists, try to set up virtual environment
                print("   Setting up virtual environment...")
                venv_path = f"{container_task_path}/.venv"

                # Create venv
                ret_venv, out_venv, err_venv = executor.execute(
                    ["uv", "venv", venv_path],
                    workdir=container_task_path,
                    env={"UV_CACHE_DIR": "/tasks/.uv_cache"}
                )

                if ret_venv == 0:
                    print("   ✓ Virtual environment created")
                    venv_python = f"{venv_path}/bin/python"

                    # Install requirements
                    ret_pip, out_pip, err_pip = executor.execute(
                        ["uv", "pip", "install", "-r", f"{container_task_path}/requirements.txt", "--python", venv_python],
                        workdir=container_task_path,
                        env={"UV_CACHE_DIR": "/tasks/.uv_cache"}
                    )

                    if ret_pip == 0:
                        print("   ✓ Requirements installed")
                        python_executable = venv_python
                    else:
                        print("   ⚠️ Failed to install requirements, using system python")
                else:
                    print("   ⚠️ Failed to create virtual environment, using system python")

            # Run the test script with live output
            test_script = "/tasks/test_runner_script_ng.py"
            test_command = [python_executable, test_script, "--task-dir", container_task_path, "--runs", str(runs)]

            print(f"   Running: {' '.join(test_command)}")
            print("   " + "="*50)

            ret_test, out_test, err_test = executor.execute(test_command, workdir=container_task_path)

            # Print all output from the test runner
            if out_test.strip():
                print(out_test)
            if err_test.strip():
                print(f"\n{'-'*20} STDERR OUTPUT {'-'*20}")
                print(err_test)
                print("-" * 50)

            print("   " + "="*50)

            # Determine success based on exit code
            if ret_test == 0:
                print(f"✅ Tests PASSED for {notebook_file}")
                successful_tasks.append(notebook_file)
            else:
                print(f"❌ Tests FAILED for {notebook_file} (exit code: {ret_test})")
                failed_tasks.append({
                    "notebook_file": notebook_file,
                    "step": "run_tests",
                    "error": f"Tests failed with exit code {ret_test}",
                    "stdout": out_test,
                    "stderr": err_test,
                })

        except Exception as e:
            print(f"❌ Unexpected error processing {notebook_file}: {e}")
            failed_tasks.append({
                "notebook_file": notebook_file,
                "step": "unexpected_error",
                "error": str(e),
            })

    # Print summary
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    print(f"Total tasks processed: {len(notebook_files)}")
    print(f"Successful: {len(successful_tasks)}")
    print(f"Failed: {len(failed_tasks)}")

    if successful_tasks:
        print("\n✅ Successful tasks:")
        for task_identifier in successful_tasks:
            print(f"   - {task_identifier}")

    if failed_tasks:
        print("\n❌ Failed tasks:")
        for failure in failed_tasks:
            print(f"   - {failure['notebook_file']}: {failure['error']} (step: {failure['step']})")


# === Main Entry Point ===

def main():
    parser = argparse.ArgumentParser(
        description="Standalone Novel Code Task Validator using local .ipynb files"
    )

    parser.add_argument(
        "notebook_files",
        nargs="+",
        help="One or more local .ipynb notebook files to validate"
    )

    parser.add_argument(
        "--container-id",
        required=True,
        help="Name or ID of the running sandbox container (e.g., 'ms-novel-code-sandbox')"
    )

    parser.add_argument(
        "--container-tool",
        type=ContainerTool,
        choices=list(ContainerTool),
        help="Container tool to use ('enroot', 'podman' or 'docker'). Auto-detects if omitted."
    )

    parser.add_argument(
        "--tasks-dir",
        default="./tasks",
        help="Directory to create task folders (default: './tasks')"
    )

    parser.add_argument(
        "--runs",
        type=int,
        default=10,
        help="Number of times to run each test to detect flaky behavior (default: 10)"
    )

    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove existing task folders before unpacking to ensure clean extraction"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print container stdout/stderr during execution"
    )

    args = parser.parse_args()

    # Validate runs argument
    if args.runs < 1:
        print("Error: --runs must be at least 1", file=sys.stderr)
        sys.exit(1)

    try:
        validate_notebook_tasks(
            notebook_files=args.notebook_files,
            container_id=args.container_id,
            container_tool=args.container_tool,
            tasks_dir=args.tasks_dir,
            runs=args.runs,
            clean=args.clean,
            verbose=args.verbose,
        )
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()