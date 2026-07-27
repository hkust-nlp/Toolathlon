import unittest

from main import find_preservation_mismatches, values_preserve_expected


class ValuesPreservationTests(unittest.TestCase):
    def test_additional_compatibility_keys_are_allowed(self):
        expected = {
            "master": {"persistence": {"enabled": False}},
            "auth": {"enabled": True, "password": "simple123"},
            "metrics": {"enabled": False},
        }
        actual = {
            "master": expected["master"],
            "auth": expected["auth"],
            "metrics": {
                "enabled": False,
                "image": {"repository": "bitnamilegacy/redis-exporter"},
            },
            "global": {"security": {"allowInsecureImages": True}},
            "image": {"repository": "bitnamilegacy/redis"},
            "kubectl": {
                "image": {"repository": "bitnamilegacy/kubectl"}
            },
            "sentinel": {
                "image": {"repository": "bitnamilegacy/redis-sentinel"}
            },
            "sysctl": {"image": {"repository": "bitnamilegacy/os-shell"}},
            "volumePermissions": {
                "image": {"repository": "bitnamilegacy/os-shell"}
            },
        }

        self.assertTrue(values_preserve_expected(expected, actual))

    def test_additional_nested_mapping_keys_are_allowed(self):
        expected = {
            "master": {
                "resources": {"requests": {"memory": "128Mi"}}
            }
        }
        actual = {
            "master": {
                "resources": {
                    "requests": {"memory": "128Mi", "cpu": "50m"},
                    "limits": {"memory": "256Mi"},
                }
            }
        }

        self.assertTrue(values_preserve_expected(expected, actual))

    def test_missing_or_changed_original_values_are_rejected(self):
        expected = {
            "auth": {"enabled": True},
            "replica": {"replicaCount": 2},
        }

        self.assertFalse(
            values_preserve_expected(
                expected,
                {"auth": {"enabled": True}, "replica": {}},
            )
        )
        self.assertFalse(
            values_preserve_expected(
                expected,
                {
                    "auth": {"enabled": True},
                    "replica": {"replicaCount": 3},
                },
            )
        )

    def test_lists_cannot_gain_or_lose_items(self):
        expected = {"tolerations": [{"key": "node-type"}]}
        actual = {
            "tolerations": [
                {"key": "node-type"},
                {"key": "offline-registry"},
            ]
        }

        self.assertFalse(values_preserve_expected(expected, actual))

    def test_mapping_items_inside_lists_cannot_gain_keys(self):
        expected = {"tolerations": [{"key": "node-type"}]}
        actual = {
            "tolerations": [
                {"key": "node-type", "operator": "Equal"},
            ]
        }

        self.assertFalse(values_preserve_expected(expected, actual))

    def test_scalar_types_inside_lists_must_be_preserved(self):
        self.assertFalse(values_preserve_expected([True], [1]))

    def test_scalar_types_must_be_preserved(self):
        self.assertFalse(values_preserve_expected({"enabled": True}, {"enabled": 1}))
        self.assertEqual(
            find_preservation_mismatches(
                {"enabled": True}, {"enabled": 1}
            ),
            ["$.enabled (value changed)"],
        )


if __name__ == "__main__":
    unittest.main()
