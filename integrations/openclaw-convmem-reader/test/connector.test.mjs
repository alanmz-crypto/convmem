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
  createStrictFdRoles,
  computeLaunchPayloadSha256,
  canonicalJsonBytes,
  closedErrorPayload,
} from "../index.js";

const SHA_A = `sha256:${"a".repeat(64)}`;

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
    runtime_distribution_sha256: SHA_A,
    launch_policy_sha256: SHA_A,
    manager_policy_sha256: SHA_A,
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
      kind: p.endsWith(".py") || p.includes("strict_server") ? "tree" : "file",
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
  };
  paths[manifest.service_home] = {
    kind: "dir",
    mode: 0o700,
    uid: 1001,
    gid: 1001,
    symlink: false,
  };
  paths[manifest.temp_directory] = {
    kind: "dir",
    mode: 0o700,
    uid: 1001,
    gid: 1001,
    symlink: false,
  };
  return { paths };
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
    if (eventQ.length === 0) return null;
    return eventQ.shift();
  }

  function respondToNextStdinWrite(rawEvidenceText, { isError = false, rpcId = 1 } = {}) {
    // Called after connector writes: prove stdin bytes, then script stdout.
    const written = Buffer.concat(boundRoles.stdin.writeTrace());
    const line = written.toString("utf8").split("\n").filter(Boolean).at(-1);
    const req = JSON.parse(line);
    assert.equal(req.method, "tools/call");
    const id = rpcId === "auto" ? req.id : rpcId;
    const result = {
      content: [{ type: "text", text: rawEvidenceText }],
      isError,
    };
    const frame = `${JSON.stringify({ jsonrpc: "2.0", id, result })}\n`;
    eventQ.push({
      kind: "stdout",
      bytes_b64: b64(frame),
      exit_code: null,
    });
    return { request: req, stdinBytes: written };
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
      `${JSON.stringify({
        jsonrpc: "2.0",
        id: 1,
        result: { content: [{ type: "text", text: JSON.stringify(evidencePayload()) }], isError: false },
      })}\n`,
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
          `${JSON.stringify({
            jsonrpc: "2.0",
            id: 1,
            result: {
              content: [{ type: "text", text: JSON.stringify(evidencePayload()) }],
              isError: false,
            },
          })}\n`,
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

test("case48: one active + eight pending; ninth temporarily_unavailable; FIFO; no retry", async () => {
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
    return { kind: "hang", bytes_b64: null, exit_code: null };
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

  const ninth = await session.invokeAlias("convmem_search", { query: "overflow" });
  assert.equal(ninth.isError, true);
  assert.equal(JSON.parse(ninth.content[0].text).error.code, "temporarily_unavailable");

  // Exact bytes crossed fake stdin for the active request.
  const stdinBytes = Buffer.concat(fdRoles.stdin.writeTrace());
  assert.ok(stdinBytes.byteLength > 0, "active request must write stdin");
  assert.ok(stdinBytes.includes(Buffer.from("tools/call")));

  // Release the gate and feed FIFO responses for each accepted job.
  // Re-arm gate after each response cycle so pending jobs can block again.
  async function releaseOne() {
    const lines = Buffer.concat(fdRoles.stdin.writeTrace())
      .toString("utf8")
      .split("\n")
      .filter(Boolean);
    const last = JSON.parse(lines.at(-1));
    const evidence = JSON.stringify(evidencePayload());
    responseQ.push({
      kind: "stdout",
      bytes_b64: b64(
        `${JSON.stringify({
          jsonrpc: "2.0",
          id: last.id,
          result: { content: [{ type: "text", text: evidence }], isError: false },
        })}\n`,
      ),
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
  for (const r of results) {
    assert.equal(r.isError, false);
    assert.match(r.content[0].text, /"instruction_authority":"none"/);
  }
  assert.equal(spawnLog.length, 1);
  // No automatic retry after the ninth denial — still a single spawn.
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
    const written = Buffer.concat(session.fdRoles.stdin.writeTrace());
    assert.ok(written.byteLength > 0);
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
