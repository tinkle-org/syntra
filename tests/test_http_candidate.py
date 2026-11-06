"""Static proposal regression tests, not HTTP/TLS/Noise runtime conformance."""

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
# The reviewed bundle was already on main here. Keep preservation checks usable
# after the acceptance PR is squash-merged and its feature branch is deleted.
REVIEWED_BUNDLE_REVISION = "729bc8761db886a41fbc33e6f2c9dcf407026428"
ACCEPTANCE_REFERENCE = {
    "public_approval_url": "https://github.com/tinkle-org/syntra/pull/25#issuecomment-6688499482",
    "reviewed_revision": "cfab7655c348f1d04f4e1d57e28cc1a634478854",
    "record_path": "docs/decisions/0004-rfc-0011-0014-acceptance.md",
}
SPEC = importlib.util.spec_from_file_location("http_candidate", ROOT / "scripts/check-http-candidate.py")
assert SPEC is not None and SPEC.loader is not None
C = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(C)


class HttpCandidateTests(unittest.TestCase):
    """Exercise isolated proposal validation without claiming runtime conformance."""

    def setUp(self):
        """Load candidate inputs, canonical contexts, and the context encoder."""
        self.contract = C.load(ROOT, f"{C.BUNDLE}/contract.json")
        self.contexts = C.load(ROOT, f"{C.BUNDLE}/context-vectors.json")
        self.base = C.load(ROOT, "conformance/test-vectors/connection/context-vectors.json")
        self.encode = C.context_encoder(ROOT)

    def test_isolated_bundle_and_active_base_are_consistent(self):
        """Check fingerprint coverage and the report's non-release authority."""
        report = C.validate(ROOT)
        self.assertEqual(report["kind"], "worktree-not-release")
        self.assertIsNone(report["source"]["candidate_revision"])
        self.assertEqual(report["runtime_conformance"], "NOT_EXECUTED")
        for gate in ("maintainer_consent_reported", "self_approval_disclosed",
                     "public_approval", "human_security_review", "accepted"):
            with self.subTest(gate=gate):
                self.assertIs(report["authority"][gate], True)
        for gate in ("active", "freeze", "release_authorized"):
            with self.subTest(gate=gate):
                self.assertIs(report["authority"][gate], False)
        self.assertEqual(report["authority"]["formal_conformance"], "NOT_EXECUTED")
        self.assertEqual(report["status"], "accepted-unadopted")
        self.assertEqual(report["acceptance_reference"], ACCEPTANCE_REFERENCE)
        self.assertEqual(report["acceptance_reference_validation"],
                         "local-reference-consistency-only-not-GitHub-authorization")
        self.assertEqual(report["source"]["base_revision"],
                         "3f7e8ea037fefcc5c86101d23e7722c83e28a0d3")
        # Original schema inventory plus the append-only RPC case owner.
        self.assertEqual(len(report["base_git_blobs_sha256"]), len(C.BASE_FILES) + 8 + 1)
        self.assertEqual(set(report["files_sha256"]), set(C.SOURCE_FILES))
        record = ACCEPTANCE_REFERENCE["record_path"]
        self.assertIn(record, report["files_sha256"])
        self.assertEqual(report["files_sha256"][record], C.sha(C.read_bounded(ROOT, record)))

    def test_candidate_validation_jobs_fetch_pinned_base_history(self):
        """Require full Git history in jobs that validate pinned base blobs."""
        for workflow, job in (("repo-validation.yml", "docs"),
                              ("repo-validation.yml", "conformance"),
                              ("release-please.yml", "validate")):
            config = yaml.safe_load(C.read_bounded(ROOT, f".github/workflows/{workflow}"))
            checkout = next(step for step in config["jobs"][job]["steps"]
                            if step.get("uses", "").startswith("actions/checkout@"))
            with self.subTest(workflow=workflow, job=job):
                self.assertEqual(checkout.get("with", {}).get("fetch-depth", 1), 0,
                                 "candidate validation needs the pinned base Git objects")

    def test_base_guard_rejects_active_owner_edits_without_writing_files(self):
        """Reject simulated edits to every guarded canonical and governance input."""
        read = C.read_bounded
        self.assertIn("GOVERNANCE.md", C.BASE_FILES)
        for target in C.BASE_FILES:
            with self.subTest(target=target), mock.patch.object(
                    C, "read_bounded", side_effect=lambda root, path:
                    b"unauthorized active edit" if path == target else read(root, path)):
                with self.assertRaisesRegex(ValueError, "active input changed before adoption"):
                    C.verify_base(ROOT)

    def test_worktree_report_rejects_source_changes_during_validation(self):
        """Reject candidate inputs that change while validation is running."""
        original = C.read_bounded
        for target in (C.SOURCE_FILES[0], ACCEPTANCE_REFERENCE["record_path"]):
            reads = 0

            def changing(root, path):
                """Simulate a source or decision changing after its initial hash."""
                nonlocal reads
                raw = original(root, path)
                if path == target:
                    reads += 1
                    if reads > 1:
                        return raw + b"changed during validation"
                return raw

            with self.subTest(target=target), mock.patch.object(C, "read_bounded", side_effect=changing):
                with self.assertRaisesRegex(ValueError, "candidate source changed during validation"):
                    C.validate(ROOT)

    def test_accepted_design_is_valid_without_adoption_or_release(self):
        """Accept the recorded design state without raising active/release authority."""
        accepted = copy.deepcopy(self.contract)
        accepted["status"] = "accepted-unadopted"
        accepted["authority"].update(public_approval=True, human_security_review=True, accepted=True)
        accepted["acceptance_reference"] = copy.deepcopy(ACCEPTANCE_REFERENCE)
        C.validate_contract(accepted)
        self.assertEqual(self.contract, accepted, "checked-in bundle must match the accepted design")

    def test_accepted_contract_rejects_malformed_or_elevated_gates(self):
        """Reject mistyped, missing, lowered, elevated, or unrecognized gates."""
        C.validate_contract(self.contract)
        for gate, expected in self.contract["authority"].items():
            values = (not expected, 0, 1, None, "true", [], {}) if type(expected) is bool else (
                "PASS", True, None)
            for value in values:
                changed = copy.deepcopy(self.contract)
                changed["authority"][gate] = value
                with self.subTest(gate=gate, value=value), self.assertRaises(ValueError):
                    C.validate_contract(changed)
            changed = copy.deepcopy(self.contract)
            del changed["authority"][gate]
            with self.subTest(missing=gate), self.assertRaises(ValueError):
                C.validate_contract(changed)
        for changes in ({"accepted": 0}, {"formal_conformance": "PASS"}, {"unrecorded_gate": True}):
            changed = copy.deepcopy(self.contract)
            changed["authority"].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                C.validate_contract(changed)

    def test_acceptance_reference_drift_is_rejected(self):
        """Require the exact public URL, reviewed revision and local decision path."""
        self.assertEqual(self.contract["acceptance_reference"], ACCEPTANCE_REFERENCE)
        C.validate_contract(self.contract)
        for key in ACCEPTANCE_REFERENCE:
            for value in ("", None, "unrelated", "../outside", True):
                changed = copy.deepcopy(self.contract)
                changed["acceptance_reference"][key] = value
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    C.validate_contract(changed)
            changed = copy.deepcopy(self.contract)
            del changed["acceptance_reference"][key]
            with self.subTest(missing=key), self.assertRaises(ValueError):
                C.validate_contract(changed)
        for reference in (None, {}, dict(ACCEPTANCE_REFERENCE, github_verified=True)):
            changed = copy.deepcopy(self.contract)
            changed["acceptance_reference"] = reference
            with self.subTest(reference=reference), self.assertRaises(ValueError):
                C.validate_contract(changed)
        changed = copy.deepcopy(self.contract)
        del changed["acceptance_reference"]
        with self.assertRaises(ValueError):
            C.validate_contract(changed)

    def test_acceptance_record_must_exist_and_match_local_references(self):
        """Reject absent or inconsistent records; no GitHub authorization is inferred."""
        reference = copy.deepcopy(ACCEPTANCE_REFERENCE)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(FileNotFoundError):
                C.validate_acceptance_reference(root, reference)
            record = root / reference["record_path"]
            record.parent.mkdir(parents=True)
            for text in ("", reference["public_approval_url"], reference["reviewed_revision"],
                         reference["public_approval_url"] + "\n" + reference["reviewed_revision"]):
                record.write_text(text)
                with self.subTest(text=text), self.assertRaises(ValueError):
                    C.validate_acceptance_reference(root, reference)
            record.write_bytes(C.read_bounded(ROOT, reference["record_path"]))
            C.validate_acceptance_reference(root, reference)

    def test_bundle_status_labels_remain_accepted_unadopted(self):
        """Keep every machine artifact accepted but inactive, without runtime PASS."""
        for name in ("contract.json", "profiles.yaml", "cases.yaml", "requirements.yaml",
                     "context-vectors.json", "http-vectors.json"):
            with self.subTest(name=name):
                data = C.load(ROOT, f"{C.BUNDLE}/{name}")
                self.assertEqual(data["status"], "accepted-unadopted")
                if "runtime_verdict" in data:
                    self.assertEqual(data["runtime_verdict"], "NOT_EXECUTED")

    def test_rejected_decision_disposition_with_retained_references_is_rejected(self):
        """Do not report accepted authority from references to a rejected design."""
        read = C.read_bounded
        path = ACCEPTANCE_REFERENCE["record_path"]
        record = read(ROOT, path)
        disposition = b"**Accepted as an optional additive pre-release design; canonical adoption\ndeferred.**"
        self.assertEqual(record.count(disposition), 1)
        changed = record.replace(disposition, b"**Rejected.**")
        for key in ("public_approval_url", "reviewed_revision"):
            self.assertIn(ACCEPTANCE_REFERENCE[key].encode(), changed)
        with mock.patch.object(C, "read_bounded", side_effect=lambda root, name:
                               changed if name == path else read(root, name)):
            with self.assertRaisesRegex(ValueError, "RFC 0013 disposition must be Accepted"):
                C.validate(ROOT)

    def test_acceptance_record_rejects_duplicate_rfc_0013_sections(self):
        """Count every RFC 0013 heading regardless of disposition formatting."""
        record = C.read_bounded(ROOT, ACCEPTANCE_REFERENCE["record_path"])
        for disposition in (b"Rejected.", b"**Rejected.**", b""):
            duplicate = b"### RFC 0013: Conflicting disposition\n\n" + disposition + b"\n\n"
            for changed in (duplicate + record, record + b"\n" + duplicate):
                with self.subTest(disposition=disposition, prepended=changed.startswith(duplicate)):
                    with mock.patch.object(C, "read_bounded", return_value=changed):
                        with self.assertRaisesRegex(ValueError, "exactly one RFC 0013 section"):
                            C.validate_acceptance_reference(ROOT, ACCEPTANCE_REFERENCE)

    def test_acceptance_disposition_cannot_come_from_another_section(self):
        """Keep the accepted disposition inside the sole RFC 0013 section."""
        record = C.read_bounded(ROOT, ACCEPTANCE_REFERENCE["record_path"])
        changed = record.replace(b"**Accepted as an optional additive pre-release design;",
                                 b"### RFC 9999: Unrelated\n\n**Accepted as an optional additive pre-release design;")
        self.assertNotEqual(changed, record)
        with mock.patch.object(C, "read_bounded", return_value=changed):
            with self.assertRaisesRegex(ValueError, "RFC 0013 disposition must be Accepted"):
                C.validate_acceptance_reference(ROOT, ACCEPTANCE_REFERENCE)

    def test_reviewed_fixture_bytes_and_contract_constants_are_preserved(self):
        """Allow only status labels in fixtures and acceptance metadata in the contract."""
        revision = REVIEWED_BUNDLE_REVISION
        for name in ("profiles.yaml", "cases.yaml", "requirements.yaml",
                     "context-vectors.json", "http-vectors.json"):
            path = f"{C.BUNDLE}/{name}"
            original = C.git(ROOT, "show", f"{revision}:{path}")
            with self.subTest(name=name):
                self.assertEqual(original.count(b"pending-adoption"), 1)
                self.assertEqual(C.read_bounded(ROOT, path), original.replace(
                    b"pending-adoption", b"accepted-unadopted", 1))
        original = json.loads(C.git(ROOT, "show", f"{revision}:{C.BUNDLE}/contract.json"))
        current = copy.deepcopy(self.contract)
        self.assertEqual(current.pop("acceptance_reference"), ACCEPTANCE_REFERENCE)
        for key in ("status", "authority"):
            original.pop(key)
            current.pop(key)
        self.assertEqual(current, original)

    def test_runtime_verdicts_cannot_be_elevated_by_acceptance(self):
        """Reject PASS and malformed runtime verdicts in both manifests."""
        cases = C.load(ROOT, f"{C.BUNDLE}/cases.yaml")
        requirements = C.load(ROOT, f"{C.BUNDLE}/requirements.yaml")
        current = C.load(ROOT, "conformance/manifest/requirements.yaml")
        rfc = C.read_bounded(ROOT, "rfcs/0013-http-tls-carriers.md").decode()
        for name, data, validate in (
                ("cases", cases, lambda value: C.validate_cases(value, rfc)),
                ("requirements", requirements,
                 lambda value: C.validate_requirements(value, cases, current))):
            validate(data)
            for verdict in ("PASS", "FAIL", True, None):
                changed = copy.deepcopy(data)
                changed["runtime_verdict"] = verdict
                with self.subTest(name=name, verdict=verdict), self.assertRaises(ValueError):
                    validate(changed)

    def test_main_rfc_must_be_accepted_not_draft_or_active(self):
        """Reject stale or elevated RFC labels even when the bundle is accepted."""
        read = C.read_bounded
        path = "rfcs/0013-http-tls-carriers.md"
        rfc = read(ROOT, path)
        self.assertIn(b"- Status: Accepted\n", rfc)
        for status in (b"Draft", b"Active", b"Accepted\n- Status: Draft"):
            changed = rfc.replace(b"- Status: Accepted", b"- Status: " + status)
            with self.subTest(status=status), mock.patch.object(
                    C, "read_bounded", side_effect=lambda root, name:
                    changed if name == path else read(root, name)):
                with self.assertRaisesRegex(ValueError, "RFC status must be Accepted"):
                    C.validate(ROOT)

    def test_contract_rejects_bad_mapping_or_security_constants(self):
        """Reject drift in HTTP mappings, limits, and TLS trust boundaries."""
        for field, value in (("send_ack_requires_decryption", True),
                             ("send_ack_requires_runtime_consumption", True),
                             ("automatic_rpc_replay", True), ("streams", 3),
                             ("status_204_content_length", "required")):
            changed = copy.deepcopy(self.contract)
            changed["http"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                C.validate_contract(changed)
        for path in ("/syntra/http/send", "/syntra/1.0/http/send?route=x"):
            changed = copy.deepcopy(self.contract)
            changed["http"]["operations"]["send"]["path"] = path
            with self.assertRaises(ValueError):
                C.validate_contract(changed)
        changed = copy.deepcopy(self.contract)
        changed["limits"]["poll_hold_ms_max"] = 30001
        with self.assertRaises(ValueError):
            C.validate_contract(changed)
        changed = copy.deepcopy(self.contract)
        changed["tls_provider"]["forwarded_claims"] = True
        with self.assertRaises(ValueError):
            C.validate_contract(changed)
        changed = copy.deepcopy(self.contract)
        changed["http"]["extra_authentication"] = True
        with self.assertRaises(ValueError):
            C.validate_contract(changed)

    def test_current_encoder_still_rejects_unadopted_carriers_by_default(self):
        """Keep proposed carriers opt-in for isolated context encoding only."""
        for code in (4, 5):
            case = dict(self.base["contexts"][0], carrier=code)
            with self.assertRaises(ValueError):
                self.encode(case)
            self.assertEqual(len(self.encode(case, permitted_carriers=(4, 5))), 35)
    def test_public_context_bytes_and_negative_recipes(self):
        """Check context bytes, negative recipes, and UTF-8 scope bounds."""
        C.validate_contexts(self.contexts, self.base, self.encode)
        changed = copy.deepcopy(self.contexts)
        changed["contexts"][0]["context_hex"] += "00"
        with self.assertRaises(ValueError):
            C.validate_contexts(changed, self.base, self.encode)
        changed = copy.deepcopy(self.contexts)
        changed["negative_recipes"][0]["changes"]["carrier"] = 4
        with self.assertRaises(ValueError):
            C.validate_contexts(changed, self.base, self.encode)
        # Scope byte bounds, UTF-8 and upper numeric fields reuse the source encoder.
        for code in (4, 5):
            for scope in ("a", "é", "a" * 255):
                case = dict(self.base["contexts"][0], carrier=code, scope=scope)
                self.assertEqual(len(self.encode(case, permitted_carriers=(4, 5))), 34 + len(scope.encode()))
            with self.assertRaises(ValueError):
                self.encode(dict(case, scope="é" * 128), permitted_carriers=(4, 5))

    def test_http_shapes_and_ack_are_structural_not_authentication(self):
        """Check HTTP fixture coverage without treating ACKs as authentication."""
        data = C.load(ROOT, f"{C.BUNDLE}/http-vectors.json")
        C.validate_http(data)
        rows = C.materialize_http(data["vectors"])
        self.assertEqual(C.lint_http_shape(rows["R13-H02"]), "accept")
        self.assertFalse(rows["R13-H02"]["attests"]["noise_authenticated"])
        self.assertFalse(rows["R13-H02"]["attests"]["runtime_consumed"])
        for name in ("R13-H05", "R13-H06", "R13-H07", "R13-H09", "R13-H10", "R13-H12", "R13-H14", "R13-H25"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                C.lint_http_shape(rows[name])
        self.assertEqual(C.lint_http_shape(rows["R13-H15"]), "tunnel")
        self.assertEqual(bytes.fromhex(rows["R13-H15"]["read_ahead_hex"]), b"\x16\x03\x03")
        self.assertEqual({(row["operation"], row["direction"]) for row in rows.values()
                          if row["expected"] == "accept"},
                         {(op, side) for op in ("open", "send", "poll", "close")
                          for side in ("request", "response")})
        self.assertEqual(len(bytes.fromhex(rows["R13-H23"]["body_hex"])), 65535)
        with self.assertRaises(ValueError):
            C.lint_http_shape(rows["R13-H24"])

    def test_http_fixture_mutations_and_bounds_fail_closed(self):
        """Reject unsafe headers, invalid mutation bases, and oversized fills."""
        row = C.materialize_http(C.load(ROOT, f"{C.BUNDLE}/http-vectors.json")["vectors"])["R13-H01"]
        for header in (["Injected\r\nName", "1"], ["X-Test", "bad\r\nvalue"],
                       ["X-Test", "x" * 4096], ["Syntra-Poll", "0"],
                       ["Content-Encoding", "identity"],
                       ["Connection", "keep-alive, close"],
                       ["Connection", "Close"],
                       ["Connection", " keep-alive , CLOSE "]):
            changed = copy.deepcopy(row)
            changed["headers"].append(header)
            with self.subTest(header=header[0]), self.assertRaises(ValueError):
                C.lint_http_shape(changed)
        with self.assertRaises(ValueError):
            C.materialize_http([{"id": "x", "base": "missing"}])
        with self.assertRaises(ValueError):
            C.materialize_http([dict(row, append_zero_bytes=65537)])

    def test_registry_does_not_enable_claims_or_conflict_with_active_codes(self):
        """Keep proposed carrier entries isolated, unclaimable, and Noise-bound."""
        profiles = C.load(ROOT, f"{C.BUNDLE}/profiles.yaml")
        current = C.load(ROOT, "conformance/profiles.yaml")
        C.validate_profiles(profiles, self.contract, current)
        for field, value in (("claimable", True), ("carrier", 3), ("integral_noise", False)):
            changed = copy.deepcopy(profiles)
            changed["profiles"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                C.validate_profiles(changed, self.contract, current)

    def test_cases_have_reciprocal_trace_without_execution_claim(self):
        """Reject case trace drift, invalid IDs, and inverted expectations."""
        cases = C.load(ROOT, f"{C.BUNDLE}/cases.yaml")
        rfc = C.read_bounded(ROOT, "rfcs/0013-http-tls-carriers.md").decode()
        C.validate_cases(cases, rfc)
        for change in ("missing-case", "unknown-requirement", "pass-verdict", "remove-role",
                       "inverted-positive", "inverted-negative", "bad-case-id"):
            changed = copy.deepcopy(cases)
            if change == "missing-case":
                changed["cases"].pop()
            elif change == "unknown-requirement":
                changed["cases"][0]["requirements"].append("R13-99")
            elif change == "pass-verdict":
                changed["runtime_verdict"] = "PASS"
            elif change == "inverted-positive":
                key = next(iter(changed["cases"][0]["positive_expected"]))
                changed["cases"][0]["positive_expected"][key] = False
            elif change == "inverted-negative":
                key = next(iter(changed["cases"][0]["negative_expected"]))
                changed["cases"][0]["negative_expected"][key] = True
            elif change == "bad-case-id":
                changed["cases"][0]["id"] = "R13-T01|.*"
            else:
                changed["cases"][0]["roles"] = ["client"]
            with self.subTest(change=change), self.assertRaises(ValueError):
                C.validate_cases(changed, rfc)

    def test_canonical_snapshot_adoption_retains_consent_gates(self):
        """Distinguish fulfilled review from deferred canonical adoption in docs."""
        readme = " ".join(C.read_bounded(ROOT, f"{C.BUNDLE}/README.md").decode().split())
        for wording in (
                "public acceptance",
                "human protocol/security self-review",
                "self-approval",
                "canonical adoption remains pending",
                "synchronized canonical specification, registry and fixture changes",
                "real reviewed commit and verified blobs"):
            with self.subTest(wording=wording):
                self.assertIn(wording, readme)

    def test_tls_variants_have_separate_wss_and_https_groups(self):
        """Confine paired-stream TLS assertions to the HTTPS carrier group."""
        cases = C.load(ROOT, f"{C.BUNDLE}/cases.yaml")
        tls = next(case for case in cases["cases"] if case["id"] == "R13-T10")
        variants = tls["input"]["variants"]
        self.assertTrue(all(isinstance(group, dict) for group in variants),
                        "TLS variants must have explicit carrier-scoped groups")
        self.assertEqual([group["carriers"] for group in variants], [[3], [5]])
        wss, https = variants
        paired = {"wrong_d_identity", "wrong_d_policy_generation",
                  "equal_authority_deadline_different_generation",
                  "policy_replacement_between_handshakes"}
        self.assertTrue(paired.isdisjoint(wss["scenarios"]))
        self.assertTrue(paired <= set(https["scenarios"]))
        self.assertTrue(set(wss["scenarios"]) <= set(https["scenarios"]))
        self.assertIn("selected_policy_withdrawal", wss["scenarios"])
        self.assertNotIn("mixed_generation_pair_accepted", tls["negative_expected"])
        self.assertFalse(https["negative_expected"]["mixed_generation_pair_accepted"])
        self.assertEqual(cases["runtime_verdict"], "NOT_EXECUTED")

    def test_tls_variant_scope_mutations_are_rejected(self):
        """Reject malformed TLS groups, scenario coverage, and assertions."""
        cases = C.load(ROOT, f"{C.BUNDLE}/cases.yaml")
        rfc = C.read_bounded(ROOT, "rfcs/0013-http-tls-carriers.md").decode()
        C.validate_cases(cases, rfc)
        for change in ("missing-wss", "missing-https", "unscoped", "mixed-carriers",
                       "pair-on-wss", "missing-pair", "unscoped-pair-expectation",
                       "nonboolean-assertion", "duplicate-scenario", "missing-common"):
            changed = copy.deepcopy(cases)
            tls = next(case for case in changed["cases"] if case["id"] == "R13-T10")
            groups = tls["input"]["variants"]
            if change == "missing-wss":
                groups.pop(0)
            elif change == "missing-https":
                groups.pop()
            elif change == "unscoped":
                del groups[0]["carriers"]
            elif change == "mixed-carriers":
                groups[0]["carriers"] = [3, 5]
            elif change == "pair-on-wss":
                groups[0]["scenarios"].append("wrong_d_policy_generation")
            elif change == "missing-pair":
                groups[1]["scenarios"].remove("wrong_d_policy_generation")
            elif change == "unscoped-pair-expectation":
                tls["negative_expected"]["mixed_generation_pair_accepted"] = False
            elif change == "nonboolean-assertion":
                groups[1]["negative_expected"]["mixed_generation_pair_accepted"] = "false"
            elif change == "duplicate-scenario":
                groups[0]["scenarios"].append(groups[0]["scenarios"][0])
            else:
                groups[0]["scenarios"].remove("selected_policy_withdrawal")
            with self.subTest(change=change), self.assertRaises(ValueError):
                C.validate_cases(changed, rfc)

    def test_requirement_owner_mapping_is_local_collision_free_and_reciprocal(self):
        """Reject requirement ID collisions, owner drift, and broken case traces."""
        requirements = C.load(ROOT, f"{C.BUNDLE}/requirements.yaml")
        cases = C.load(ROOT, f"{C.BUNDLE}/cases.yaml")
        active = C.load(ROOT, "conformance/manifest/requirements.yaml")
        C.validate_requirements(requirements, cases, active)
        for field, value in (("test_ids", []), ("proposed_requirement_id", "SNTR-HPC-029"),
                             ("owner", "specifications/security.md")):
            changed = copy.deepcopy(requirements)
            changed["requirements"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                C.validate_requirements(changed, cases, active)

    def test_duplicate_keys_path_escape_symlinks_and_file_caps_rejected(self):
        """Reject ambiguous mappings and unsafe or oversized file inputs."""
        with self.assertRaises(ValueError):
            json.loads('{"a":1,"a":2}', object_pairs_hook=C.unique_pairs)
        with self.assertRaises(ValueError):
            yaml.load("a: 1\na: 2\n", Loader=C.UniqueYaml)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "large").write_bytes(b"x" * (C.MAX_FILE + 1))
            (root / "link").symlink_to(root / "large")
            for name in ("../outside", "/absolute", "link", "large"):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    C.read_bounded(root, name)

    def test_adoption_command_is_explicitly_blocked(self):
        """Keep exit 2 for canonical adoption, not already fulfilled review gates."""
        result = subprocess.run([sys.executable, "scripts/check-http-candidate.py", "--require-adoption"],
                                cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("canonical adoption pending", result.stderr)
        self.assertIn("public approval and human security self-review recorded", result.stderr)
        self.assertNotIn("human security review and canonical activation are pending", result.stderr)


if __name__ == "__main__":
    unittest.main()
