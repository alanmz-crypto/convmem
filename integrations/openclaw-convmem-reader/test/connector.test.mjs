/**
 * M5/T4 connector tests — non-vacuous queue/write-trace evidence for cases
 * 2, 33, 35, 48, 57, 58 (connector portions only). No real child/process.
 */
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import test from "node:test";
import {
  RUNTIME_NOT_QUALIFIED,
  TOOL_ALIASES,
  MCP_METHODS,
  register,
  activate,
  validateLaunchTuple,
  createConnectorSession,
  computeLaunchPayloadSha256,
  canonicalJsonBytes,
  closedErrorPayload,
} from "../index.js";

const SHA_A = `sha256:${"a".repeat(64)}`;
/** Independently supplied capability digests (not host-derived). */
const SHA_RUNTIME = `sha256:${"b".repeat(64)}`;
const SHA_LAUNCH = `sha256:${"c".repeat(64)}`;
const SHA_MANAGER = `sha256:${"d".repeat(64)}`;
const DEADLINE_MS = 10_000;
const MAX_REQUEST_BYTES = 128 * 1024;
const MAX_RESPONSE_BYTES = 64 * 1024;

function baseManifest(overrides = {}) {
  const body = {
    schema: "convmem.openclaw-connector-launch.v2",
    python_executable: "/runtime/bin/python",
    python_executable_sha256: SHA_A,
    strict_server_path: "/src/openclaw_strict_server.py",
    strict_server_tree_sha256: SHA_A,
    working_directory: "/fixture/empty",
    scope_file: "/fixture/scope.json",
    registry_file: "/fixture/registry.json",
    strict_config_file: "/fixture/strict-config.json",
    scope_sha256: SHA_A,
    registry_sha256: SHA_A,
    strict_config_sha256: SHA_A,
    service_home: "/fixture/home",
    path_value: "/runtime/bin",
    lang: "C.UTF-8",
    lc_all: "C.UTF-8",
    temp_directory: "/fixture/tmp",
    setpriv_executable: "/runtime/bin/setpriv",
    setpriv_sha256: SHA_A,
    seccomp_filter_file: "/runtime/filter.bpf",
    seccomp_filter_sha256: SHA_A,
    runtime_distribution_sha256: SHA_RUNTIME,
    launch_policy_sha256: SHA_LAUNCH,
    manager_policy_sha256: SHA_MANAGER,
    launch_payload_sha256: SHA_A,
    ...overrides,
  };
  body.launch_payload_sha256 = computeLaunchPayloadSha256(body);
  return body;
}

function virtualPathCaps(manifest) {
  const paths = {};
  const filePaths = [
    manifest.python_executable,
    manifest.strict_server_path,
    manifest.scope_file,
    manifest.registry_file,
    manifest.strict_config_file,
    manifest.setpriv_executable,
    manifest.seccomp_filter_file,
  ];
  for (const p of filePaths) {
    paths[p] = {
      kind: "file",
      mode: 0o444,
      uid: 0,
      gid: 0,
      symlink: false,
      digest: SHA_A,
    };
  }
  paths[manifest.strict_server_path].kind = "tree";
  paths[manifest.working_directory] = {
    kind: "dir",
    mode: 0o555,
    uid: 0,
    gid: 0,
    symlink: false,
    empty: true,
  };
  paths[manifest.service_home] = {
    kind: "dir",
    mode: 0o700,
    uid: 1001,
    gid: 1001,
    symlink: false,
    credentials: false,
  };
  paths[manifest.temp_directory] = {
    kind: "dir",
    mode: 0o700,
    uid: 1001,
    gid: 1001,
    symlink: false,
    bounded: true,
  };
  return {
    paths,
    // Independently supplied — must match manifest pins or fail closed.
    runtime_distribution_sha256: manifest.runtime_distribution_sha256,
    launch_policy_sha256: manifest.launch_policy_sha256,
    manager_policy_sha256: manifest.manager_policy_sha256,
  };
}

function hangEvent() {
  return { kind: "hang", bytes_b64: null, exit_code: null };
}

function b64(bytes) {
  return Buffer.from(bytes).toString("base64");
}

function evidencePayload() {
  return {
    schema: "convmem.raw-evidence.v3",
    instruction_authority: "none",
    snapshot: {
      snapshot_id: "snap2_test",
      lineage_id: "lin2_test",
      authority_seq: 1,
      authority_manifest_sha256: SHA_A,
      semantic_contract_sha256: SHA_A,
      state_basis: "complete_bound_authority",
      verification_basis: "recorded_qualified_checks",
      as_of: "2026-09-20T00:00:00Z",
      expires_at: "2026-09-21T00:00:00Z",
    },
    selection_complete: true,
    display_basis: "ranked_selection",
    results: [],
  };
}

function rpcStdoutFrame(id, rawEvidenceText, { isError = false } = {}) {
  const result = {
    content: [{ type: "text", text: rawEvidenceText }],
    isError,
  };
  return `${JSON.stringify({ jsonrpc: "2.0", id, result })}\n`;
}

/**
 * Test-owned injected transport: validates spawn tuple logging + scripts
 * stdout/exit via next_event. Bytes written to stdin are traced.
 */
function createFakeTransport({
  scripted = null,
  onSpawn = null,
  clock = { t: 1_000 },
} = {}) {
  const spawnLog = [];
  const eventQ = [];
  let handleCounter = 0;
  let boundRoles = null;
  let boundHandle = null;

  if (Array.isArray(scripted)) {
    for (const ev of scripted) eventQ.push(ev);
  }

  function spawn(role, argv, env, cwd, fd_roles) {
    const rec = {
      role,
      argv: [...argv],
      env: { ...env },
      cwd,
      fd_role_keys: Object.keys(fd_roles || {}).sort(),
    };
    spawnLog.push(rec);
    if (typeof onSpawn === "function") onSpawn(rec, fd_roles);
    boundRoles = fd_roles;
    handleCounter += 1;
    boundHandle = handleCounter.toString(16).padStart(32, "0");
    return boundHandle;
  }

  function next_event(handle) {
    assert.equal(handle, boundHandle);
    // Empty schedule uses an explicit hang event — null/undefined are malformed.
    if (eventQ.length === 0) return hangEvent();
    return eventQ.shift();
  }

  function respondToNextStdinWrite(rawEvidenceText, { isError = false, rpcId = 1 } = {}) {
    // Transport read path: consume live queued stdin (resets per-frame capacity).
    // writeTrace is immutable evidence and is not the read path.
    const live = boundRoles.stdin.drain();
    assert.ok(live.byteLength > 0, "fake must consume live stdin queue bytes");
    const line = live.toString("utf8").split("\n").filter(Boolean).at(-1);
    const req = JSON.parse(line);
    assert.equal(req.method, "tools/call");
    const id = rpcId === "auto" ? req.id : rpcId;
    const frame = rpcStdoutFrame(id, rawEvidenceText, { isError });
    eventQ.push({
      kind: "stdout",
      bytes_b64: b64(frame),
      exit_code: null,
    });
    const evidence = Buffer.concat(boundRoles.stdin.writeTrace());
    return { request: req, stdinBytes: live, writeTraceBytes: evidence };
  }

  function pushEvent(ev) {
    eventQ.push(ev);
  }

  return {
    spawn,
    next_event,
    spawnLog,
    eventQ,
    get fdRoles() {
      return boundRoles;
    },
    respondToNextStdinWrite,
    pushEvent,
    now: () => clock.t,
    clock,
  };
}

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

test("case2: exactly three frozen aliases map one-to-one to MCP methods", () => {
  assert.deepEqual(Object.keys(TOOL_ALIASES).sort(), [
    "convmem_related",
    "convmem_search",
    "convmem_unresolved",
  ]);
  assert.deepEqual(Object.values(TOOL_ALIASES).sort(), [...MCP_METHODS].sort());
  assert.equal(TOOL_ALIASES.convmem_search, "search");
  assert.equal(TOOL_ALIASES.convmem_unresolved, "unresolved");
  assert.equal(TOOL_ALIASES.convmem_related, "related");
  assert.equal(TOOL_ALIASES.convmem_ask, undefined);
  assert.equal(TOOL_ALIASES.search, undefined);
});

test("validateLaunchTuple accepts closed manifest and rejects bad self-hash", () => {
  const manifest = baseManifest();
  const caps = virtualPathCaps(manifest);
  const launch = validateLaunchTuple(manifest, caps);
  assert.equal(launch.role, "strict_server");
  assert.deepEqual(launch.argv, [
    "/runtime/bin/setpriv",
    "--no-new-privs",
    "--seccomp-filter",
    "/runtime/filter.bpf",
    "/runtime/bin/python",
    "-B",
    "-s",
    "/src/openclaw_strict_server.py",
  ]);
  assert.deepEqual(launch.env, {
    CONVMEM_MCP_PROFILE: "openclaw-strict",
    CONVMEM_BOUND_READ_SCOPE_FILE: "/fixture/scope.json",
    CONVMEM_PROJECT_BINDING_REGISTRY_FILE: "/fixture/registry.json",
    CONVMEM_STRICT_CONFIG_FILE: "/fixture/strict-config.json",
    HOME: "/fixture/home",
    PATH: "/runtime/bin",
    LANG: "C.UTF-8",
    LC_ALL: "C.UTF-8",
    TMPDIR: "/fixture/tmp",
  });
  assert.equal(launch.cwd, "/fixture/empty");

  const bad = { ...manifest, launch_payload_sha256: SHA_A };
  assert.throws(() => validateLaunchTuple(bad, caps), /launch_payload_sha256/);
});

test("launch_payload_sha256 matches parent canonical JSON excluding only itself", () => {
  const manifest = baseManifest();
  const body = { ...manifest };
  delete body.launch_payload_sha256;
  const expected = `sha256:${createHash("sha256")
    .update(canonicalJsonBytes(body))
    .digest("hex")}`;
  assert.equal(computeLaunchPayloadSha256(manifest), expected);
  assert.equal(manifest.launch_payload_sha256, expected);
});

test("capability proof fails closed without paths or required attrs", () => {
  const manifest = baseManifest();
  assert.throws(() => validateLaunchTuple(manifest, {}), /capability_paths/);
  assert.throws(() => validateLaunchTuple(manifest, { paths: null }), /capability_paths/);

  const missingEntry = virtualPathCaps(manifest);
  delete missingEntry.paths[manifest.scope_file];
  assert.throws(() => validateLaunchTuple(manifest, missingEntry), /capability_missing/);

  const missingKind = virtualPathCaps(manifest);
  delete missingKind.paths[manifest.scope_file].kind;
  assert.throws(() => validateLaunchTuple(manifest, missingKind), /capability_missing_attr/);

  const missingMode = virtualPathCaps(manifest);
  delete missingMode.paths[manifest.scope_file].mode;
  assert.throws(() => validateLaunchTuple(manifest, missingMode), /capability_missing_attr/);

  const missingUid = virtualPathCaps(manifest);
  delete missingUid.paths[manifest.scope_file].uid;
  assert.throws(() => validateLaunchTuple(manifest, missingUid), /capability_missing_attr/);

  const missingGid = virtualPathCaps(manifest);
  delete missingGid.paths[manifest.scope_file].gid;
  assert.throws(() => validateLaunchTuple(manifest, missingGid), /capability_missing_attr/);

  const missingDigest = virtualPathCaps(manifest);
  delete missingDigest.paths[manifest.scope_file].digest;
  assert.throws(() => validateLaunchTuple(manifest, missingDigest), /capability_missing_attr/);

  const missingRuntime = virtualPathCaps(manifest);
  delete missingRuntime.runtime_distribution_sha256;
  assert.throws(
    () => validateLaunchTuple(manifest, missingRuntime),
    /capability_missing:runtime_distribution_sha256/,
  );

  const missingLaunch = virtualPathCaps(manifest);
  delete missingLaunch.launch_policy_sha256;
  assert.throws(
    () => validateLaunchTuple(manifest, missingLaunch),
    /capability_missing:launch_policy_sha256/,
  );

  const missingManager = virtualPathCaps(manifest);
  delete missingManager.manager_policy_sha256;
  assert.throws(
    () => validateLaunchTuple(manifest, missingManager),
    /capability_missing:manager_policy_sha256/,
  );

  const mismatchRuntime = virtualPathCaps(manifest);
  mismatchRuntime.runtime_distribution_sha256 = SHA_A;
  assert.throws(
    () => validateLaunchTuple(manifest, mismatchRuntime),
    /capability_digest:runtime_distribution_sha256/,
  );

  const mismatchLaunch = virtualPathCaps(manifest);
  mismatchLaunch.launch_policy_sha256 = SHA_A;
  assert.throws(
    () => validateLaunchTuple(manifest, mismatchLaunch),
    /capability_digest:launch_policy_sha256/,
  );

  const mismatchManager = virtualPathCaps(manifest);
  mismatchManager.manager_policy_sha256 = SHA_A;
  assert.throws(
    () => validateLaunchTuple(manifest, mismatchManager),
    /capability_digest:manager_policy_sha256/,
  );

  const badCwd = virtualPathCaps(manifest);
  badCwd.paths[manifest.working_directory].empty = false;
  assert.throws(() => validateLaunchTuple(manifest, badCwd), /capability_cwd_empty/);

  const badHome = virtualPathCaps(manifest);
  badHome.paths[manifest.service_home].credentials = true;
  assert.throws(() => validateLaunchTuple(manifest, badHome), /capability_home_credentials/);

  const badHomeUid = virtualPathCaps(manifest);
  badHomeUid.paths[manifest.service_home].uid = 0;
  assert.throws(() => validateLaunchTuple(manifest, badHomeUid), /capability_uid/);

  const missingHomeGid = virtualPathCaps(manifest);
  delete missingHomeGid.paths[manifest.service_home].gid;
  assert.throws(() => validateLaunchTuple(manifest, missingHomeGid), /capability_missing_attr/);

  const missingTempMode = virtualPathCaps(manifest);
  delete missingTempMode.paths[manifest.temp_directory].mode;
  assert.throws(() => validateLaunchTuple(manifest, missingTempMode), /capability_missing_attr/);

  const badTempGid = virtualPathCaps(manifest);
  badTempGid.paths[manifest.temp_directory].gid = 0;
  assert.throws(() => validateLaunchTuple(manifest, badTempGid), /capability_uid/);

  const badTemp = virtualPathCaps(manifest);
  badTemp.paths[manifest.temp_directory].bounded = false;
  assert.throws(() => validateLaunchTuple(manifest, badTemp), /capability_temp_bounded/);

  const badInputGid = virtualPathCaps(manifest);
  badInputGid.paths[manifest.scope_file].gid = 1001;
  assert.throws(() => validateLaunchTuple(manifest, badInputGid), /capability_uid/);

  const traversal = baseManifest({
    scope_file: "/fixture/../etc/passwd",
  });
  assert.throws(
    () => validateLaunchTuple(traversal, virtualPathCaps(traversal)),
    /path_traversal/,
  );
});

test("case33: tool args cannot inject argv/env/cwd/paths; closed env only at spawn", async () => {
  const manifest = baseManifest();
  const caps = virtualPathCaps(manifest);
  const fake = createFakeTransport();
  const session = createConnectorSession({
    manifest,
    spawn: fake.spawn,
    nextEvent: fake.next_event,
    capabilityData: caps,
    now: fake.now,
  });

  assert.equal(fake.spawnLog.length, 1);
  const spawned = fake.spawnLog[0];
  assert.equal(spawned.role, "strict_server");
  assert.deepEqual(spawned.env, session.launchTuple.env);
  assert.equal(Object.keys(spawned.env).sort().join(","), [
    "CONVMEM_BOUND_READ_SCOPE_FILE",
    "CONVMEM_MCP_PROFILE",
    "CONVMEM_PROJECT_BINDING_REGISTRY_FILE",
    "CONVMEM_STRICT_CONFIG_FILE",
    "HOME",
    "LANG",
    "LC_ALL",
    "PATH",
    "TMPDIR",
  ].join(","));
  assert.equal(spawned.env.CONVMEM_MCP_PROFILE, "openclaw-strict");
  // Hostile legacy keys must not appear.
  assert.equal(spawned.env.OPENAI_API_KEY, undefined);
  assert.equal(spawned.env.CONVMEM_READ_SCOPE, undefined);

  const evidence = JSON.stringify(evidencePayload());
  const pending = session.invokeAlias("convmem_search", {
    query: "x",
    argv: "/bin/evil",
    cwd: "/tmp/evil",
    env: { OPENAI_API_KEY: "leak" },
    config_path: "/etc/passwd",
    registry_path: "/etc/passwd",
    scope_file: "/etc/passwd",
  });
  queueMicrotask(() => {
    const { request, stdinBytes } = fake.respondToNextStdinWrite(evidence, {
      rpcId: "auto",
    });
    assert.ok(stdinBytes.byteLength > 0, "exact bytes must cross fake stdin");
    assert.equal(request.params.name, "search");
    // Injection attempts in args must not alter spawn tuple or MCP method name mapping.
    assert.equal(request.params.arguments.argv, "/bin/evil");
    assert.deepEqual(fake.spawnLog[0].argv, session.launchTuple.argv);
  });

  const result = await pending;
  assert.equal(result.isError, false);
  assert.equal(result.content[0].text, evidence);
  assert.match(result.content[0].text, /"instruction_authority":"none"/);
});

test("case2/evidence: raw strict-server bytes preserved in standard tool-result block", async () => {
  const manifest = baseManifest();
  const fake = createFakeTransport();
  const session = createConnectorSession({
    manifest,
    spawn: fake.spawn,
    nextEvent: fake.next_event,
    capabilityData: virtualPathCaps(manifest),
    now: fake.now,
  });
  const raw = JSON.stringify(evidencePayload());
  const pending = session.invokeAlias("convmem_search", { query: "q" });
  queueMicrotask(() => {
    fake.respondToNextStdinWrite(raw, { rpcId: "auto" });
  });
  const result = await pending;
  assert.deepEqual(Object.keys(result).sort(), ["content", "isError"]);
  assert.equal(result.content.length, 1);
  assert.equal(result.content[0].type, "text");
  assert.equal(result.content[0].text, raw);
  // No invented OpenClaw-specific envelope fields.
  assert.equal(result.envelope, undefined);
  assert.equal(result.untrusted_evidence, undefined);
  const parsed = JSON.parse(result.content[0].text);
  assert.equal(parsed.instruction_authority, "none");
  assert.equal(parsed.schema, "convmem.raw-evidence.v3");
});

test("case35: child exit before response is failure; no late success", async () => {
  const manifest = baseManifest();
  const fake = createFakeTransport({
    scripted: [{ kind: "exit", bytes_b64: null, exit_code: 9 }],
  });
  const session = createConnectorSession({
    manifest,
    spawn: fake.spawn,
    nextEvent: fake.next_event,
    capabilityData: virtualPathCaps(manifest),
    now: fake.now,
  });
  const result = await session.invokeAlias("convmem_unresolved", { limit: 5 });
  assert.equal(result.isError, true);
  const err = JSON.parse(result.content[0].text);
  assert.equal(err.schema, "convmem.error.v1");
  assert.equal(err.error.code, "internal_failure");

  // Late stdout after exit must not convert the settled failure into success.
  fake.pushEvent({
    kind: "stdout",
    bytes_b64: b64(
      rpcStdoutFrame(1, JSON.stringify(evidencePayload())),
    ),
    exit_code: null,
  });
  assert.equal(session.terminated, true);
});

test("case35: cancel discards late success", async () => {
  const manifest = baseManifest();
  const clock = { t: 1_000 };
  const fake = createFakeTransport({ clock });
  const session = createConnectorSession({
    manifest,
    spawn: fake.spawn,
    nextEvent: () => {
      // First poll: cancel, then attempt to deliver success.
      session.cancel("convmem_related");
      return {
        kind: "stdout",
        bytes_b64: b64(
          rpcStdoutFrame(1, JSON.stringify(evidencePayload())),
        ),
        exit_code: null,
      };
    },
    capabilityData: virtualPathCaps(manifest),
    now: () => clock.t,
  });
  const result = await session.invokeAlias("convmem_related", {
    ledger_id: "obs2_test",
  });
  assert.equal(result.isError, true);
  assert.equal(JSON.parse(result.content[0].text).error.code, "internal_failure");
});

test("case48: one active + eight pending; ninth denied; FIFO identity; one stdin write each", async () => {
  const manifest = baseManifest();
  const clock = { t: 1_000 };
  const responseQ = [];
  let gateResolve = null;
  let gate = new Promise((r) => {
    gateResolve = r;
  });
  const spawnLog = [];
  let boundHandle = null;
  let fdRoles = null;
  let handleCounter = 0;

  function spawn(role, argv, env, cwd, roles) {
    spawnLog.push({ role, argv: [...argv], env: { ...env }, cwd });
    fdRoles = roles;
    handleCounter += 1;
    boundHandle = handleCounter.toString(16).padStart(32, "0");
    return boundHandle;
  }

  function next_event(handle) {
    assert.equal(handle, boundHandle);
    if (responseQ.length > 0) {
      return responseQ.shift();
    }
    return hangEvent();
  }

  const session = createConnectorSession({
    manifest,
    spawn,
    nextEvent: next_event,
    capabilityData: virtualPathCaps(manifest),
    now: () => clock.t,
    pollWait: () => gate,
  });

  const promises = [];
  for (let i = 0; i < 9; i += 1) {
    promises.push(session.invokeAlias("convmem_search", { query: `q${i}` }));
  }
  // Let the first job become active and block in pollWait; pending fills to 8.
  await Promise.resolve();
  await Promise.resolve();
  await Promise.resolve();

  const writesBeforeDenied = fdRoles.stdin.writeTrace().length;
  assert.equal(writesBeforeDenied, 1, "exactly one stdin write for the active call");
  // Live bytes remain until the fake transport consumes them.
  assert.ok(fdRoles.stdin.byteLength > 0, "writer must not self-drain stdin");

  const ninth = await session.invokeAlias("convmem_search", { query: "overflow" });
  assert.equal(ninth.isError, true);
  assert.equal(JSON.parse(ninth.content[0].text).error.code, "temporarily_unavailable");
  assert.equal(
    fdRoles.stdin.writeTrace().length,
    writesBeforeDenied,
    "denied call must not write stdin or retry",
  );
  const deniedTrace = Buffer.concat(fdRoles.stdin.writeTrace()).toString("utf8");
  assert.equal(deniedTrace.includes('"query":"overflow"'), false);

  // Exact bytes crossed fake stdin for the active request (still live until drain).
  const stdinBytes = fdRoles.stdin.peekAll();
  assert.ok(stdinBytes.byteLength > 0, "active request must write stdin");
  assert.ok(stdinBytes.includes(Buffer.from("tools/call")));

  // Release the gate and feed FIFO responses for each accepted job by request id.
  async function releaseOne() {
    const live = fdRoles.stdin.drain();
    assert.ok(live.byteLength > 0, "fake must drain queued request bytes");
    const last = JSON.parse(live.toString("utf8").split("\n").filter(Boolean).at(-1));
    const evidence = JSON.stringify({
      ...evidencePayload(),
      fifo_query: last.params.arguments.query,
      fifo_id: last.id,
    });
    responseQ.push({
      kind: "stdout",
      bytes_b64: b64(rpcStdoutFrame(last.id, evidence)),
      exit_code: null,
    });
    const prev = gateResolve;
    gate = new Promise((r) => {
      gateResolve = r;
    });
    prev();
    await Promise.resolve();
    await Promise.resolve();
  }

  for (let i = 0; i < 9; i += 1) {
    await releaseOne();
  }
  // Final unlock in case a waiter remains.
  gateResolve();

  const results = await Promise.all(promises);
  assert.equal(results.length, 9);
  for (let i = 0; i < 9; i += 1) {
    const r = results[i];
    assert.equal(r.isError, false);
    const body = JSON.parse(r.content[0].text);
    assert.equal(body.instruction_authority, "none");
    assert.equal(body.fifo_query, `q${i}`, "FIFO by request-specific identity");
    assert.equal(body.fifo_id, i + 1);
  }
  assert.equal(fdRoles.stdin.writeTrace().length, 9, "one stdin write per accepted call");
  assert.equal(spawnLog.length, 1);
  // No automatic retry after the ninth denial — still a single spawn.
});

test("exact 10s scripted-clock deadline fails without invented poll-count cutoff", async () => {
  const manifest = baseManifest();
  const clock = { t: 5_000 };
  let hangPolls = 0;
  const session = createConnectorSession({
    manifest,
    spawn: () => "a".repeat(32),
    nextEvent: () => ({ kind: "hang", bytes_b64: null, exit_code: null }),
    capabilityData: virtualPathCaps(manifest),
    now: () => clock.t,
    pollWait: async () => {
      hangPolls += 1;
      // Advance only after well past the old invented 256-poll cap would have fired.
      if (hangPolls === 300) {
        clock.t = 5_000 + DEADLINE_MS + 1;
      }
    },
  });
  const result = await session.invokeAlias("convmem_search", { query: "deadline" });
  assert.equal(result.isError, true);
  assert.equal(JSON.parse(result.content[0].text).error.code, "internal_failure");
  assert.ok(hangPolls >= 300, "must survive beyond 256 polls until scripted 10s elapses");
  assert.equal(clock.t, 5_000 + DEADLINE_MS + 1);
});

test("partial frame succeeds before deadline; incomplete frame fails at deadline", async () => {
  const manifest = baseManifest();
  const evidence = JSON.stringify(evidencePayload());

  // Success path: two stdout chunks assemble one newline-terminated frame.
  {
    const clock = { t: 1_000 };
    let phase = 0;
    const session = createConnectorSession({
      manifest,
      spawn: () => "b".repeat(32),
      nextEvent: () => {
        if (phase === 0) {
          phase = 1;
          return {
            kind: "ready",
            bytes_b64: null,
            exit_code: null,
          };
        }
        if (phase === 1) {
          phase = 2;
          const prefix = `{"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":`;
          return { kind: "stdout", bytes_b64: b64(prefix), exit_code: null };
        }
        if (phase === 2) {
          phase = 3;
          const suffix = `${JSON.stringify(evidence)}}],"isError":false}}\n`;
          return { kind: "stdout", bytes_b64: b64(suffix), exit_code: null };
        }
        return hangEvent();
      },
      capabilityData: virtualPathCaps(manifest),
      now: () => clock.t,
    });
    const ok = await session.invokeAlias("convmem_search", { query: "partial-ok" });
    assert.equal(ok.isError, false);
    assert.equal(ok.content[0].text, evidence);
  }

  // Failure path: incomplete frame until scripted deadline.
  {
    const clock = { t: 2_000 };
    let polls = 0;
    const session = createConnectorSession({
      manifest,
      spawn: () => "c".repeat(32),
      nextEvent: () => {
        if (polls === 0) {
          polls = 1;
          return {
            kind: "stdout",
            bytes_b64: b64('{"jsonrpc":"2.0","id":1,"result":'),
            exit_code: null,
          };
        }
        return { kind: "hang", bytes_b64: null, exit_code: null };
      },
      capabilityData: virtualPathCaps(manifest),
      now: () => clock.t,
      pollWait: async () => {
        clock.t = 2_000 + DEADLINE_MS + 1;
      },
    });
    const bad = await session.invokeAlias("convmem_search", { query: "partial-fail" });
    assert.equal(bad.isError, true);
    assert.equal(JSON.parse(bad.content[0].text).error.code, "internal_failure");
  }
});

test("64KiB stdout overflow fails closed as response_too_large", async () => {
  const manifest = baseManifest();
  const clock = { t: 1_000 };
  const oversize = Buffer.alloc(MAX_RESPONSE_BYTES + 1, 0x61);
  const session = createConnectorSession({
    manifest,
    spawn: () => "d".repeat(32),
    nextEvent: () => ({
      kind: "stdout",
      bytes_b64: b64(oversize),
      exit_code: null,
    }),
    capabilityData: virtualPathCaps(manifest),
    now: () => clock.t,
  });
  const result = await session.invokeAlias("convmem_search", { query: "overflow64" });
  assert.equal(result.isError, true);
  assert.equal(JSON.parse(result.content[0].text).error.code, "response_too_large");
  assert.equal(session.terminated, true);
});

test("next_event contract rejects extra fields, unknown kinds, and non-canonical base64", async () => {
  const manifest = baseManifest();

  async function expectEventReject(badEvent) {
    const clock = { t: 1_000 };
    const session = createConnectorSession({
      manifest,
      spawn: () => "e".repeat(32),
      nextEvent: () => badEvent,
      capabilityData: virtualPathCaps(manifest),
      now: () => clock.t,
    });
    const result = await session.invokeAlias("convmem_search", { query: "bad-event" });
    assert.equal(result.isError, true);
    assert.equal(JSON.parse(result.content[0].text).error.code, "internal_failure");
    assert.equal(session.terminated, true);
  }

  await expectEventReject({
    kind: "stdout",
    bytes_b64: b64("x\n"),
    exit_code: null,
    extra: true,
  });
  await expectEventReject({
    kind: "unknown",
    bytes_b64: null,
    exit_code: null,
  });
  await expectEventReject({
    kind: "stdout",
    bytes_b64: "$$$$",
    exit_code: null,
  });
  await expectEventReject({
    kind: "ready",
    bytes_b64: null,
    exit_code: null,
    again: 1,
  });
  await expectEventReject({
    kind: "exit",
    bytes_b64: null,
    exit_code: 1.5,
  });
});

test("next_event null/undefined is malformed and terminates", async () => {
  const manifest = baseManifest();
  for (const bad of [null, undefined]) {
    const clock = { t: 1_000 };
    const session = createConnectorSession({
      manifest,
      spawn: () => "1".repeat(32),
      nextEvent: () => bad,
      capabilityData: virtualPathCaps(manifest),
      now: () => clock.t,
    });
    const result = await session.invokeAlias("convmem_search", { query: "null-event" });
    assert.equal(result.isError, true);
    assert.equal(JSON.parse(result.content[0].text).error.code, "internal_failure");
    assert.equal(session.terminated, true);
  }
});

test("ready is allowed once per session; second ready in same request fails", async () => {
  const manifest = baseManifest();
  const clock = { t: 1_000 };
  let n = 0;
  const session = createConnectorSession({
    manifest,
    spawn: () => "f".repeat(32),
    nextEvent: () => {
      n += 1;
      return { kind: "ready", bytes_b64: null, exit_code: null };
    },
    capabilityData: virtualPathCaps(manifest),
    now: () => clock.t,
  });
  const result = await session.invokeAlias("convmem_search", { query: "ready-twice" });
  assert.equal(result.isError, true);
  assert.equal(JSON.parse(result.content[0].text).error.code, "internal_failure");
  assert.equal(session.terminated, true);
  assert.ok(n >= 2);
});

test("ready once per spawned handle: second request cannot re-ready", async () => {
  const manifest = baseManifest();
  const fake = createFakeTransport();
  const session = createConnectorSession({
    manifest,
    spawn: fake.spawn,
    nextEvent: fake.next_event,
    capabilityData: virtualPathCaps(manifest),
    now: fake.now,
  });
  const raw = JSON.stringify(evidencePayload());

  const first = session.invokeAlias("convmem_search", { query: "ready-first" });
  queueMicrotask(() => {
    fake.pushEvent({ kind: "ready", bytes_b64: null, exit_code: null });
    fake.respondToNextStdinWrite(raw, { rpcId: "auto" });
  });
  const ok = await first;
  assert.equal(ok.isError, false);

  const second = session.invokeAlias("convmem_search", { query: "ready-again" });
  queueMicrotask(() => {
    // Cross-request second ready on the same handle must fail closed.
    fake.pushEvent({ kind: "ready", bytes_b64: null, exit_code: null });
    fake.respondToNextStdinWrite(raw, { rpcId: "auto" });
  });
  const bad = await second;
  assert.equal(bad.isError, true);
  assert.equal(JSON.parse(bad.content[0].text).error.code, "internal_failure");
  assert.equal(session.terminated, true);
});

test("per-frame caps are not cumulative across consumed calls; writeTrace stays", async () => {
  const manifest = baseManifest();
  const fake = createFakeTransport();
  const session = createConnectorSession({
    manifest,
    spawn: fake.spawn,
    nextEvent: fake.next_event,
    capabilityData: virtualPathCaps(manifest),
    now: fake.now,
  });

  const raw = JSON.stringify(evidencePayload());
  // Each frame individually under 128KiB; aggregate writeTrace exceeds 128KiB.
  const chunkQuery = "x".repeat(50 * 1024);
  let aggregate = 0;
  for (let i = 0; i < 3; i += 1) {
    const pending = session.invokeAlias("convmem_search", {
      query: `cap-${i}-${chunkQuery}`,
    });
    queueMicrotask(() => {
      // Live queue must still hold the frame until fake consumption.
      assert.ok(session.fdRoles.stdin.byteLength > 0);
      assert.ok(session.fdRoles.stdin.byteLength <= MAX_REQUEST_BYTES);
      fake.respondToNextStdinWrite(raw, { rpcId: "auto" });
    });
    const result = await pending;
    assert.equal(result.isError, false);
    // Live queue size resets after receiver drain, not writer self-drain.
    assert.equal(session.fdRoles.stdin.byteLength, 0);
    assert.equal(session.fdRoles.stdout.byteLength, 0);
  }
  const trace = session.fdRoles.stdin.writeTrace();
  assert.equal(trace.length, 3);
  for (const b of trace) {
    assert.ok(b.byteLength <= MAX_REQUEST_BYTES);
    assert.ok(b.byteLength > 50 * 1024);
    aggregate += b.byteLength;
  }
  assert.ok(
    aggregate > MAX_REQUEST_BYTES,
    `aggregate writeTrace ${aggregate} must exceed 128KiB`,
  );
  const joined = Buffer.concat(trace).toString("utf8");
  assert.match(joined, /cap-0-/);
  assert.match(joined, /cap-1-/);
  assert.match(joined, /cap-2-/);
});

test("output partial-frame accounting resets only after consumption/completion", async () => {
  const manifest = baseManifest();
  const clock = { t: 1_000 };
  const evidence = JSON.stringify(evidencePayload());
  let phase = 0;
  let roles = null;
  const session = createConnectorSession({
    manifest,
    spawn: (_role, _argv, _env, _cwd, fd) => {
      roles = fd;
      return "2".repeat(32);
    },
    nextEvent: () => {
      if (phase === 0) {
        phase = 1;
        const prefix = `{"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":`;
        return { kind: "stdout", bytes_b64: b64(prefix), exit_code: null };
      }
      if (phase === 1) {
        // Partial bytes must still occupy the output frame capacity.
        assert.ok(roles.stdout.byteLength > 0, "partial must remain queued until completion");
        phase = 2;
        const suffix = `${JSON.stringify(evidence)}}],"isError":false}}\n`;
        return { kind: "stdout", bytes_b64: b64(suffix), exit_code: null };
      }
      return hangEvent();
    },
    capabilityData: virtualPathCaps(manifest),
    now: () => clock.t,
  });
  const ok = await session.invokeAlias("convmem_search", { query: "partial-reset" });
  assert.equal(ok.isError, false);
  assert.equal(ok.content[0].text, evidence);
  // Capacity resets only after the completed frame is consumed.
  assert.equal(session.fdRoles.stdout.byteLength, 0);
});

test("output frame cap resets after completed consumption for next request", async () => {
  const manifest = baseManifest();
  const fake = createFakeTransport();
  const session = createConnectorSession({
    manifest,
    spawn: fake.spawn,
    nextEvent: fake.next_event,
    capabilityData: virtualPathCaps(manifest),
    now: fake.now,
  });
  // Large but valid text payloads: each response under 64KiB; two together exceed.
  const bigText = "y".repeat(40 * 1024);
  for (let i = 0; i < 2; i += 1) {
    const pending = session.invokeAlias("convmem_search", { query: `out-cap-${i}` });
    queueMicrotask(() => {
      fake.respondToNextStdinWrite(bigText, { rpcId: "auto" });
    });
    const result = await pending;
    assert.equal(result.isError, false);
    assert.equal(result.content[0].text, bigText);
    assert.equal(session.fdRoles.stdout.byteLength, 0);
  }
  const outTrace = session.fdRoles.stdout.writeTrace();
  assert.equal(outTrace.length, 2);
  const outAgg = outTrace.reduce((n, b) => n + b.byteLength, 0);
  assert.ok(outAgg > MAX_RESPONSE_BYTES);
  for (const b of outTrace) {
    assert.ok(b.byteLength <= MAX_RESPONSE_BYTES);
  }
});

test("stdout trailing bytes after one newline frame are protocol desync", async () => {
  const manifest = baseManifest();
  const clock = { t: 1_000 };
  const frame = rpcStdoutFrame(1, JSON.stringify(evidencePayload()));
  const desync = Buffer.from(`${frame}trailing-garbage`, "utf8");
  const session = createConnectorSession({
    manifest,
    spawn: () => "3".repeat(32),
    nextEvent: () => ({
      kind: "stdout",
      bytes_b64: b64(desync),
      exit_code: null,
    }),
    capabilityData: virtualPathCaps(manifest),
    now: () => clock.t,
  });
  const result = await session.invokeAlias("convmem_search", { query: "desync-tail" });
  assert.equal(result.isError, true);
  assert.equal(JSON.parse(result.content[0].text).error.code, "internal_failure");
  assert.equal(session.terminated, true);
});

test("case48: oversized request frame denied; malformed response fails closed; no retry", async () => {
  const manifest = baseManifest();
  const fake = createFakeTransport();
  const session = createConnectorSession({
    manifest,
    spawn: fake.spawn,
    nextEvent: fake.next_event,
    capabilityData: virtualPathCaps(manifest),
    now: fake.now,
  });

  const huge = "x".repeat(128 * 1024);
  const over = await session.invokeAlias("convmem_search", { query: huge });
  // Frame includes JSON wrapper so query alone at 128KiB overflows.
  assert.equal(over.isError, true);

  // Malformed frame: deliver non-JSON stdout after a normal-sized request.
  const pending = session.invokeAlias("convmem_search", { query: "ok" });
  queueMicrotask(() => {
    const live = session.fdRoles.stdin.drain();
    assert.ok(live.byteLength > 0);
    fake.pushEvent({
      kind: "stdout",
      bytes_b64: b64("not-json\n"),
      exit_code: null,
    });
  });
  const bad = await pending;
  assert.equal(bad.isError, true);
  assert.equal(JSON.parse(bad.content[0].text).error.code, "internal_failure");
  // Session terminates on protocol desync — no automatic retry path.
  assert.equal(session.terminated, true);
});

test("case57: every spawn crosses injected fake port with fd_roles queues", () => {
  const manifest = baseManifest();
  const seen = [];
  const fake = createFakeTransport({
    onSpawn: (rec, fd) => {
      seen.push({
        role: rec.role,
        fd_roles: ["stderr", "stdin", "stdout"].every((k) => fd[k] && fd[k].role),
        stdinRole: fd.stdin.role,
      });
    },
  });
  createConnectorSession({
    manifest,
    spawn: fake.spawn,
    nextEvent: fake.next_event,
    capabilityData: virtualPathCaps(manifest),
    now: fake.now,
  });
  assert.equal(fake.spawnLog.length, 1);
  assert.deepEqual(fake.spawnLog[0].fd_role_keys, ["stderr", "stdin", "stdout"]);
  assert.equal(seen[0].fd_roles, true);
  assert.equal(seen[0].stdinRole, "strict-stdin");
  assert.equal(seen[0].role, "strict_server");
});

test("case57: scripted filter-load failure stops before spawn/child", () => {
  const manifest = baseManifest();
  const caps = { ...virtualPathCaps(manifest), filter_load_failed: true };
  let spawned = 0;
  assert.throws(
    () =>
      createConnectorSession({
        manifest,
        spawn: () => {
          spawned += 1;
          return "a".repeat(32);
        },
        nextEvent: () => null,
        capabilityData: caps,
      }),
    /seccomp_filter_load/,
  );
  assert.equal(spawned, 0);
});

test("case58: plugin surface stays the three hashed files; validateLaunchTuple present", async () => {
  const fs = await import("node:fs");
  const path = await import("node:path");
  const { fileURLToPath } = await import("node:url");
  const pluginRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
  const names = fs.readdirSync(pluginRoot).filter((n) => !n.startsWith("."));
  assert.deepEqual(names.sort(), ["index.js", "openclaw.plugin.json", "package.json", "test"]);
  const index = fs.readFileSync(path.join(pluginRoot, "index.js"), "utf8");
  assert.match(index, /validateLaunchTuple/);
  assert.match(index, /createConnectorSession/);
  assert.match(index, /TOOL_ALIASES/);
  // No new production dependency manifests.
  assert.equal(fs.existsSync(path.join(pluginRoot, "package-lock.json")), false);
  assert.equal(fs.existsSync(path.join(pluginRoot, "node_modules")), false);
});

test("T4 virtual path/mode/ownership: writable capability digest denied; host stat unused", () => {
  const manifest = baseManifest();
  const caps = virtualPathCaps(manifest);
  caps.paths[manifest.scope_file].mode = 0o644; // owner-write bit set
  assert.throws(() => validateLaunchTuple(manifest, caps), /capability_writable/);

  const caps2 = virtualPathCaps(manifest);
  caps2.paths[manifest.scope_file].symlink = true;
  assert.throws(() => validateLaunchTuple(manifest, caps2), /capability_symlink/);

  const caps3 = virtualPathCaps(manifest);
  caps3.paths[manifest.scope_file].digest = `sha256:${"b".repeat(64)}`;
  assert.throws(() => validateLaunchTuple(manifest, caps3), /capability_digest/);
});

test("closed error envelope unchanged for temporarily_unavailable", () => {
  const payload = closedErrorPayload("temporarily_unavailable", "a".repeat(32));
  assert.deepEqual(payload, {
    schema: "convmem.error.v1",
    error: {
      code: "temporarily_unavailable",
      message: "The evidence service is temporarily unavailable.",
    },
    correlation_id: "a".repeat(32),
  });
});

test("fd_roles write trace proves non-vacuous stdin crossing (no encode-only stub)", async () => {
  const manifest = baseManifest();
  const fake = createFakeTransport();
  const session = createConnectorSession({
    manifest,
    spawn: fake.spawn,
    nextEvent: fake.next_event,
    capabilityData: virtualPathCaps(manifest),
    now: fake.now,
  });
  const raw = JSON.stringify(evidencePayload());
  let traced = null;
  const pending = session.invokeAlias("convmem_search", { query: "trace-me" });
  queueMicrotask(() => {
    traced = fake.respondToNextStdinWrite(raw, { rpcId: "auto" });
  });
  const result = await pending;
  assert.ok(traced);
  assert.ok(traced.stdinBytes.includes(Buffer.from("trace-me")));
  assert.ok(traced.stdinBytes.includes(Buffer.from("tools/call")));
  assert.equal(traced.request.params.name, "search");
  assert.equal(result.content[0].text, raw);
  // Stdout path delivered the scripted bytes via next_event, not a local stub.
  assert.equal(fake.spawnLog.length, 1);
});
