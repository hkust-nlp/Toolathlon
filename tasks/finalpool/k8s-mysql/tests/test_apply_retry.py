import os
import subprocess
import tempfile
import unittest
from pathlib import Path


TASK_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = TASK_ROOT / "scripts" / "k8s_mysql.sh"


class ApplyResourcesRetryTest(unittest.TestCase):
    def run_apply(self, mode: str) -> tuple[subprocess.CompletedProcess[str], int]:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            state_path = tmp_path / "apply-count"
            resource_path = tmp_path / "resources.yaml"
            resource_path.write_text("apiVersion: v1\nkind: List\nitems: []\n")

            env = os.environ.copy()
            env.update(
                {
                    "APPLY_MODE": mode,
                    "KUBECONFIG_PATH": str(tmp_path / "kubeconfig"),
                    "RESOURCE_PATH": str(resource_path),
                    "SCRIPT_PATH": str(SCRIPT_PATH),
                    "STATE_PATH": str(state_path),
                }
            )

            shell = r'''
uv() {
  if [[ "$*" == *global_configs.podman_or_docker* ]]; then
    printf 'docker\n'
  else
    printf '\n'
  fi
}

source "$SCRIPT_PATH"
resource_yaml="$RESOURCE_PATH"

kubectl() {
  if [ "$1" != "apply" ]; then
    printf 'unexpected kubectl invocation: %s\n' "$*" >&2
    return 99
  fi

  local count=0
  if [ -f "$STATE_PATH" ]; then
    read -r count < "$STATE_PATH"
  fi
  count=$((count + 1))
  printf '%s\n' "$count" > "$STATE_PATH"

  case "$APPLY_MODE" in
    success)
      printf 'serviceaccount/default configured\n'
      return 0
      ;;
    transient)
      if [ "$count" -eq 1 ]; then
        printf 'SENTINEL_409: serviceaccounts "default" already exists\n' >&2
        return 1
      fi
      printf 'serviceaccount/default configured\n'
      return 0
      ;;
    persistent)
      printf 'SENTINEL_PERSISTENT_%s: invalid manifest\n' "$count" >&2
      return 42
      ;;
    *)
      printf 'unknown APPLY_MODE: %s\n' "$APPLY_MODE" >&2
      return 98
      ;;
  esac
}

# Keep retry tests deterministic and fast while exercising the real loop.
sleep() { :; }

apply_resources "$KUBECONFIG_PATH"
'''
            result = subprocess.run(
                ["bash", "-c", shell],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            count = int(state_path.read_text().strip())
            return result, count

    def test_transient_failure_is_logged_and_retried(self) -> None:
        result, count = self.run_apply("transient")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(count, 2)
        self.assertIn("SENTINEL_409", result.stdout)
        self.assertIn("Retrying kubectl apply", result.stdout)
        self.assertIn("Resources applied successfully (attempt 2/3)", result.stdout)

    def test_persistent_failure_exhausts_retry_budget(self) -> None:
        result, count = self.run_apply("persistent")

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(count, 3)
        for attempt in range(1, 4):
            self.assertIn(f"SENTINEL_PERSISTENT_{attempt}", result.stdout)
        self.assertIn("Failed to apply resources after 3 attempts", result.stdout)

    def test_success_is_not_retried(self) -> None:
        result, count = self.run_apply("success")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(count, 1)
        self.assertNotIn("Retrying kubectl apply", result.stdout)
        self.assertIn("Resources applied successfully (attempt 1/3)", result.stdout)


if __name__ == "__main__":
    unittest.main()
