import assert from "node:assert/strict";
import test from "node:test";
import { register, activate, RUNTIME_NOT_QUALIFIED } from "../index.js";

test("production register refuses runtime_not_qualified before effects", () => {
  assert.equal(RUNTIME_NOT_QUALIFIED, "runtime_not_qualified");
  assert.throws(
    () => register(),
    (err) => {
      assert.equal(err.message, "runtime_not_qualified");
      assert.equal(err.code, "runtime_not_qualified");
      assert.equal(err.exitCode, 78);
      return true;
    },
  );
});

test("production activate refuses runtime_not_qualified before effects", () => {
  assert.throws(() => activate(), /runtime_not_qualified/);
});

test("T4 launch-tuple validation capability absent", () => {
  assert.equal(
    typeof globalThis.validateLaunchTuple,
    "function",
    "[T4] connector launch-tuple validation capability absent",
  );
});
