/**
 * OpenClaw ConvMem reader plugin — uninstalled connector (T4 / M5).
 *
 * Production register/activate refuse with runtime_not_qualified (exit 78)
 * before any OS effect (Architecture §6.5.8). Tool traffic uses an injected
 * test-owned spawn/next_event transport and opaque stdin/stdout/stderr
 * fd_roles byte-queue capabilities — no real child, setpriv, or OpenClaw.
 */

import { createHash, randomBytes } from "node:crypto";

export const RUNTIME_NOT_QUALIFIED = "runtime_not_qualified";

/** Frozen alias → MCP method map (Execution §3). */
export const TOOL_ALIASES = Object.freeze({
  convmem_search: "search",
  convmem_unresolved: "unresolved",
  convmem_related: "related",
});

export const MCP_METHODS = Object.freeze(["search", "unresolved", "related"]);

const SCHEMA_ID = "convmem.openclaw-connector-launch.v2";
const MAX_REQUEST_BYTES = 128 * 1024;
const MAX_RESPONSE_BYTES = 64 * 1024;
const MAX_PENDING = 8;
const DEADLINE_MS = 10_000;
const SHA256_RE = /^sha256:[0-9a-f]{64}$/;
const ABS_PATH_RE = /^\//;

const MANIFEST_KEYS = Object.freeze([
  "schema",
  "python_executable",
  "python_executable_sha256",
  "strict_server_path",
  "strict_server_tree_sha256",
  "working_directory",
  "scope_file",
  "registry_file",
  "strict_config_file",
  "scope_sha256",
  "registry_sha256",
  "strict_config_sha256",
  "service_home",
  "path_value",
  "lang",
  "lc_all",
  "temp_directory",
  "setpriv_executable",
  "setpriv_sha256",
  "seccomp_filter_file",
  "seccomp_filter_sha256",
  "runtime_distribution_sha256",
  "launch_policy_sha256",
  "manager_policy_sha256",
  "launch_payload_sha256",
]);

const PATH_DIGEST_FIELDS = Object.freeze([
  ["python_executable", "python_executable_sha256"],
  ["strict_server_path", "strict_server_tree_sha256"],
  ["scope_file", "scope_sha256"],
  ["registry_file", "registry_sha256"],
  ["strict_config_file", "strict_config_sha256"],
  ["setpriv_executable", "setpriv_sha256"],
  ["seccomp_filter_file", "seccomp_filter_sha256"],
]);

const ERROR_MESSAGES = Object.freeze({
  invalid_request: "The request is invalid.",
  identifier_query_not_supported: "Ledger handles are not supported in search.",
  scope_denied: "The requested evidence chain is unavailable in this scope.",
  snapshot_stale: "The evidence snapshot is unavailable.",
  response_too_large: "The evidence response exceeds the allowed size.",
  temporarily_unavailable: "The evidence service is temporarily unavailable.",
  internal_failure: "The evidence service failed.",
});

function refuseRuntimeNotQualified() {
  const err = new Error(RUNTIME_NOT_QUALIFIED);
  err.code = "runtime_not_qualified";
  err.exitCode = 78;
  throw err;
}

export function register() {
  refuseRuntimeNotQualified();
}

export function activate() {
  return register();
}

function sortKeysDeep(value) {
  if (Array.isArray(value)) {
    return value.map(sortKeysDeep);
  }
  if (value !== null && typeof value === "object") {
    const out = {};
    for (const key of Object.keys(value).sort()) {
      out[key] = sortKeysDeep(value[key]);
    }
    return out;
  }
  return value;
}

/** Parent global canonical JSON profile (sort_keys, compact separators, UTF-8). */
export function canonicalJsonBytes(value) {
  return Buffer.from(JSON.stringify(sortKeysDeep(value)), "utf8");
}

function canonicalJsonString(value) {
  return JSON.stringify(sortKeysDeep(value));
}

export function sha256Labeled(bytes) {
  const hex = createHash("sha256").update(bytes).digest("hex");
  return `sha256:${hex}`;
}

/** Self-hash: canonical bytes excluding only launch_payload_sha256. */
export function computeLaunchPayloadSha256(manifest) {
  if (!manifest || typeof manifest !== "object") {
    throw new Error("invalid_manifest");
  }
  const body = {};
  for (const key of Object.keys(manifest).sort()) {
    if (key === "launch_payload_sha256") continue;
    body[key] = manifest[key];
  }
  return sha256Labeled(canonicalJsonBytes(body));
}

function freshCorrelationId() {
  return randomBytes(16).toString("hex");
}

export function closedErrorPayload(code, correlationId = freshCorrelationId()) {
  const message = ERROR_MESSAGES[code];
  if (!message) {
    throw new Error(`unknown_error_code:${code}`);
  }
  return {
    schema: "convmem.error.v1",
    error: { code, message },
    correlation_id: correlationId,
  };
}

function toolResultBlock(rawText, { isError = false } = {}) {
  return {
    content: [{ type: "text", text: rawText }],
    isError,
  };
}

function encodeClosedError(code) {
  return toolResultBlock(canonicalJsonString(closedErrorPayload(code)), { isError: true });
}

/**
 * Create opaque strict stdin/stdout/stderr fd_roles as bounded in-memory queues.
 * Test-owned; not a serialized production interface.
 */
export function createStrictFdRoles({
  maxStdinBytes = MAX_REQUEST_BYTES,
  maxStdoutBytes = MAX_RESPONSE_BYTES,
  maxStderrBytes = MAX_RESPONSE_BYTES,
} = {}) {
  return Object.freeze({
    stdin: createByteQueue(maxStdinBytes, "strict-stdin"),
    stdout: createByteQueue(maxStdoutBytes, "strict-stdout"),
    stderr: createByteQueue(maxStderrBytes, "strict-stderr"),
  });
}

function createByteQueue(maxBytes, role) {
  const chunks = [];
  let size = 0;
  /** Immutable per-write evidence — never cleared when live bytes are consumed. */
  const writeTrace = [];
  return {
    role,
    maxBytes,
    write(bytes) {
      const buf = Buffer.isBuffer(bytes) ? bytes : Buffer.from(bytes);
      if (size + buf.length > maxBytes) {
        const err = new Error("queue_overflow");
        err.code = "queue_overflow";
        throw err;
      }
      chunks.push(buf);
      size += buf.length;
      writeTrace.push(Buffer.from(buf));
      return buf.length;
    },
    /** Test/harness push into a readable side (stdout/stderr scripting). */
    push(bytes) {
      return this.write(bytes);
    },
    /**
     * Consume live queue bytes and reset the per-frame size cap.
     * Does not alter writeTrace evidence.
     */
    drain() {
      if (chunks.length === 0) return Buffer.alloc(0);
      const out = Buffer.concat(chunks);
      chunks.length = 0;
      size = 0;
      return out;
    },
    peekAll() {
      return Buffer.concat(chunks);
    },
    writeTrace() {
      return writeTrace.map((b) => Buffer.from(b));
    },
    get byteLength() {
      return size;
    },
  };
}

const INPUT_EXPECTED_KIND = Object.freeze({
  python_executable: "file",
  strict_server_path: "tree",
  scope_file: "file",
  registry_file: "file",
  strict_config_file: "file",
  setpriv_executable: "file",
  seccomp_filter_file: "file",
});

/** Reject symlink/traversal segments in absolute sealed paths (data-only). */
function pathHasTraversal(path) {
  if (typeof path !== "string" || path.includes("\0")) return true;
  const segments = path.split("/");
  for (let i = 1; i < segments.length; i += 1) {
    const seg = segments[i];
    if (seg === "" || seg === "." || seg === "..") return true;
  }
  return false;
}

function requireCapabilityEntry(pathCaps, path) {
  const entry = pathCaps[path];
  if (!entry || typeof entry !== "object" || Array.isArray(entry)) {
    throw launchError(`capability_missing:${path}`);
  }
  return entry;
}

function requireCapabilityAttr(entry, path, key) {
  if (!Object.prototype.hasOwnProperty.call(entry, key)) {
    throw launchError(`capability_missing_attr:${path}:${key}`);
  }
  return entry[key];
}

/** Parent-fixed simulation identities: operator 1000/1000 or root 0/0. */
function isOperatorOrRootIdentity(uid, gid) {
  return (
    (uid === 0 && gid === 0) || (uid === 1000 && gid === 1000)
  );
}

/**
 * Validate convmem.openclaw-connector-launch.v2 and the §4 launch tuple as data.
 * Virtual path/mode/ownership come from test-owned capabilityData — never host stat.
 */
export function validateLaunchTuple(manifest, capabilityData = {}) {
  if (!manifest || typeof manifest !== "object" || Array.isArray(manifest)) {
    throw launchError("invalid_manifest");
  }
  const keys = Object.keys(manifest);
  if (keys.length !== MANIFEST_KEYS.length) {
    throw launchError("manifest_key_set");
  }
  for (const key of MANIFEST_KEYS) {
    if (!Object.prototype.hasOwnProperty.call(manifest, key)) {
      throw launchError(`missing_field:${key}`);
    }
  }
  for (const key of keys) {
    if (!MANIFEST_KEYS.includes(key)) {
      throw launchError(`unknown_field:${key}`);
    }
  }
  if (manifest.schema !== SCHEMA_ID) {
    throw launchError("schema");
  }

  const pathFields = [
    "python_executable",
    "strict_server_path",
    "working_directory",
    "scope_file",
    "registry_file",
    "strict_config_file",
    "service_home",
    "temp_directory",
    "setpriv_executable",
    "seccomp_filter_file",
  ];
  for (const field of pathFields) {
    const value = manifest[field];
    if (typeof value !== "string" || !ABS_PATH_RE.test(value) || value.includes("\0")) {
      throw launchError(`path:${field}`);
    }
    if (pathHasTraversal(value)) {
      throw launchError(`path_traversal:${field}`);
    }
  }
  for (const field of [
    "python_executable_sha256",
    "strict_server_tree_sha256",
    "scope_sha256",
    "registry_sha256",
    "strict_config_sha256",
    "setpriv_sha256",
    "seccomp_filter_sha256",
    "runtime_distribution_sha256",
    "launch_policy_sha256",
    "manager_policy_sha256",
    "launch_payload_sha256",
  ]) {
    if (typeof manifest[field] !== "string" || !SHA256_RE.test(manifest[field])) {
      throw launchError(`digest:${field}`);
    }
  }
  for (const field of ["path_value", "lang", "lc_all"]) {
    if (typeof manifest[field] !== "string" || manifest[field].length < 1) {
      throw launchError(`string:${field}`);
    }
  }

  const expectedHash = computeLaunchPayloadSha256(manifest);
  if (manifest.launch_payload_sha256 !== expectedHash) {
    throw launchError("launch_payload_sha256");
  }

  // Fail closed: capability proof is mandatory and test-owned (no host fs/stat).
  if (
    !capabilityData ||
    typeof capabilityData !== "object" ||
    Array.isArray(capabilityData)
  ) {
    throw launchError("capability_data");
  }
  const caps = capabilityData;
  const pathCaps = caps.paths;
  if (!pathCaps || typeof pathCaps !== "object" || Array.isArray(pathCaps)) {
    throw launchError("capability_paths");
  }

  // Independently supplied capability digests for sealed policy/distribution pins.
  for (const field of [
    "runtime_distribution_sha256",
    "launch_policy_sha256",
    "manager_policy_sha256",
  ]) {
    if (!Object.prototype.hasOwnProperty.call(caps, field)) {
      throw launchError(`capability_missing:${field}`);
    }
    const supplied = caps[field];
    if (typeof supplied !== "string" || supplied !== manifest[field]) {
      throw launchError(`capability_digest:${field}`);
    }
  }

  for (const [pathField, digestField] of PATH_DIGEST_FIELDS) {
    const path = manifest[pathField];
    const entry = requireCapabilityEntry(pathCaps, path);
    if (requireCapabilityAttr(entry, path, "symlink") !== false) {
      throw launchError(`capability_symlink:${path}`);
    }
    const expectedKind = INPUT_EXPECTED_KIND[pathField];
    if (requireCapabilityAttr(entry, path, "kind") !== expectedKind) {
      throw launchError(`capability_kind:${path}`);
    }
    const mode = requireCapabilityAttr(entry, path, "mode");
    if (typeof mode !== "number" || (mode & 0o222) !== 0) {
      throw launchError(`capability_writable:${path}`);
    }
    const uid = requireCapabilityAttr(entry, path, "uid");
    const gid = requireCapabilityAttr(entry, path, "gid");
    if (!isOperatorOrRootIdentity(uid, gid)) {
      throw launchError(`capability_uid:${path}`);
    }
    const digest = requireCapabilityAttr(entry, path, "digest");
    if (typeof digest !== "string" || digest !== manifest[digestField]) {
      throw launchError(`capability_digest:${path}`);
    }
  }

  // Fixed empty read-only cwd — operator/root owned.
  {
    const path = manifest.working_directory;
    const entry = requireCapabilityEntry(pathCaps, path);
    if (requireCapabilityAttr(entry, path, "symlink") !== false) {
      throw launchError(`capability_symlink:${path}`);
    }
    if (requireCapabilityAttr(entry, path, "kind") !== "dir") {
      throw launchError(`capability_kind:${path}`);
    }
    if (requireCapabilityAttr(entry, path, "empty") !== true) {
      throw launchError(`capability_cwd_empty:${path}`);
    }
    const mode = requireCapabilityAttr(entry, path, "mode");
    if (typeof mode !== "number" || (mode & 0o222) !== 0) {
      throw launchError(`capability_writable:${path}`);
    }
    const uid = requireCapabilityAttr(entry, path, "uid");
    const gid = requireCapabilityAttr(entry, path, "gid");
    if (!isOperatorOrRootIdentity(uid, gid)) {
      throw launchError(`capability_uid:${path}`);
    }
  }

  // Dedicated credential-free HOME — runtime 1001/1001.
  {
    const path = manifest.service_home;
    const entry = requireCapabilityEntry(pathCaps, path);
    if (requireCapabilityAttr(entry, path, "symlink") !== false) {
      throw launchError(`capability_symlink:${path}`);
    }
    if (requireCapabilityAttr(entry, path, "kind") !== "dir") {
      throw launchError(`capability_kind:${path}`);
    }
    if (requireCapabilityAttr(entry, path, "credentials") !== false) {
      throw launchError(`capability_home_credentials:${path}`);
    }
    const mode = requireCapabilityAttr(entry, path, "mode");
    if (typeof mode !== "number") {
      throw launchError(`capability_mode:${path}`);
    }
    const uid = requireCapabilityAttr(entry, path, "uid");
    const gid = requireCapabilityAttr(entry, path, "gid");
    if (uid !== 1001 || gid !== 1001) {
      throw launchError(`capability_uid:${path}`);
    }
  }

  // Bounded temp semantics — runtime 1001/1001.
  {
    const path = manifest.temp_directory;
    const entry = requireCapabilityEntry(pathCaps, path);
    if (requireCapabilityAttr(entry, path, "symlink") !== false) {
      throw launchError(`capability_symlink:${path}`);
    }
    if (requireCapabilityAttr(entry, path, "kind") !== "dir") {
      throw launchError(`capability_kind:${path}`);
    }
    if (requireCapabilityAttr(entry, path, "bounded") !== true) {
      throw launchError(`capability_temp_bounded:${path}`);
    }
    const mode = requireCapabilityAttr(entry, path, "mode");
    if (typeof mode !== "number") {
      throw launchError(`capability_mode:${path}`);
    }
    const uid = requireCapabilityAttr(entry, path, "uid");
    const gid = requireCapabilityAttr(entry, path, "gid");
    if (uid !== 1001 || gid !== 1001) {
      throw launchError(`capability_uid:${path}`);
    }
  }

  if (caps.filter_load_failed === true) {
    throw launchError("seccomp_filter_load");
  }

  const argv = [
    manifest.setpriv_executable,
    "--no-new-privs",
    "--seccomp-filter",
    manifest.seccomp_filter_file,
    manifest.python_executable,
    "-B",
    "-s",
    manifest.strict_server_path,
  ];
  const env = {
    CONVMEM_MCP_PROFILE: "openclaw-strict",
    CONVMEM_BOUND_READ_SCOPE_FILE: manifest.scope_file,
    CONVMEM_PROJECT_BINDING_REGISTRY_FILE: manifest.registry_file,
    CONVMEM_STRICT_CONFIG_FILE: manifest.strict_config_file,
    HOME: manifest.service_home,
    PATH: manifest.path_value,
    LANG: manifest.lang,
    LC_ALL: manifest.lc_all,
    TMPDIR: manifest.temp_directory,
  };
  return Object.freeze({
    role: "strict_server",
    argv: Object.freeze([...argv]),
    env: Object.freeze({ ...env }),
    cwd: manifest.working_directory,
  });
}

function launchError(reason) {
  const err = new Error(`launch_tuple_invalid:${reason}`);
  err.code = "launch_tuple_invalid";
  err.reason = reason;
  return err;
}

const NEXT_EVENT_KINDS = Object.freeze([
  "ready",
  "stdout",
  "stderr",
  "exit",
  "hang",
]);
const NEXT_EVENT_KEYS = Object.freeze(["bytes_b64", "exit_code", "kind"]);

/** Canonical standard base64 (alphabet + padding round-trip). */
function isCanonicalBase64(value) {
  if (typeof value !== "string") return false;
  if (value.length % 4 !== 0) return false;
  if (!/^[A-Za-z0-9+/]*={0,2}$/.test(value)) return false;
  try {
    const decoded = Buffer.from(value, "base64");
    return decoded.toString("base64") === value;
  } catch {
    return false;
  }
}

/**
 * Closed next_event port: exactly {kind, bytes_b64, exit_code}.
 * Null/undefined are malformed (not idle). Empty schedules use explicit hang.
 * Fail closed on unknown kind, extra fields, or wrong null/typed payload.
 */
function parseClosedNextEvent(event, readySeen) {
  if (event === null || event === undefined) {
    return { error: "event_null" };
  }
  if (typeof event !== "object" || Array.isArray(event)) {
    return { error: "event_type" };
  }
  const keys = Object.keys(event).sort();
  if (keys.length !== NEXT_EVENT_KEYS.length) {
    return { error: "event_key_set" };
  }
  for (let i = 0; i < NEXT_EVENT_KEYS.length; i += 1) {
    if (keys[i] !== NEXT_EVENT_KEYS[i]) {
      return { error: "event_key_set" };
    }
  }
  const { kind, bytes_b64: bytesB64, exit_code: exitCode } = event;
  if (!NEXT_EVENT_KINDS.includes(kind)) {
    return { error: "event_kind" };
  }
  if (kind === "ready") {
    if (bytesB64 !== null || exitCode !== null) {
      return { error: "event_ready_fields" };
    }
    if (readySeen) {
      return { error: "event_ready_once" };
    }
    return { kind: "ready" };
  }
  if (kind === "hang") {
    if (bytesB64 !== null || exitCode !== null) {
      return { error: "event_hang_fields" };
    }
    return { kind: "hang" };
  }
  if (kind === "exit") {
    if (bytesB64 !== null) {
      return { error: "event_exit_bytes" };
    }
    if (!Number.isInteger(exitCode)) {
      return { error: "event_exit_code" };
    }
    return { kind: "exit", exitCode };
  }
  // stdout / stderr
  if (exitCode !== null) {
    return { error: "event_stream_exit_code" };
  }
  if (!isCanonicalBase64(bytesB64)) {
    return { error: "event_bytes_b64" };
  }
  return {
    kind,
    bytes: Buffer.from(bytesB64, "base64"),
  };
}

/**
 * Test/library session: inject spawn + next_event; carry fd_roles queues.
 * Private constructor name — not a plugin/config serialized contract.
 */
export function createConnectorSession({
  manifest,
  spawn,
  nextEvent,
  capabilityData = {},
  fdRoles = null,
  now = () => Date.now(),
  pollWait = null,
} = {}) {
  if (typeof spawn !== "function" || typeof nextEvent !== "function") {
    throw new Error("injected_transport_required");
  }
  const launch = validateLaunchTuple(manifest, capabilityData);
  const roles = fdRoles || createStrictFdRoles();
  if (!roles.stdin || !roles.stdout || !roles.stderr) {
    throw new Error("fd_roles_required");
  }

  const handle = spawn(launch.role, launch.argv, launch.env, launch.cwd, roles);
  if (typeof handle !== "string" || !/^[0-9a-f]{32}$/.test(handle)) {
    throw new Error("invalid_spawn_handle");
  }

  let active = null;
  const pending = [];
  let terminated = false;
  let rpcId = 0;
  /** ready is once per spawned handle/session, not once per request. */
  let sessionReadySeen = false;
  const launchTuple = launch;

  async function idleYield() {
    if (typeof pollWait === "function") {
      await pollWait();
      return;
    }
    await Promise.resolve();
  }

  function rejectIfTerminated() {
    if (terminated) {
      return encodeClosedError("internal_failure");
    }
    return null;
  }

  async function invokeAlias(alias, args = {}) {
    const early = rejectIfTerminated();
    if (early) return early;

    const method = TOOL_ALIASES[alias];
    if (!method) {
      return encodeClosedError("invalid_request");
    }
    // No dynamic name/path/argv dispatch: args cannot alter launch tuple.
    void args;

    if (active && pending.length >= MAX_PENDING) {
      return encodeClosedError("temporarily_unavailable");
    }

    const job = {
      alias,
      method,
      args: args && typeof args === "object" ? { ...args } : {},
      id: ++rpcId,
      cancelled: false,
      startedAt: null,
      settle: null,
    };
    const promise = new Promise((resolve) => {
      job.settle = resolve;
    });

    if (!active) {
      active = job;
      queueMicrotask(() => runActive());
    } else {
      pending.push(job);
    }
    return promise;
  }

  function cancel(aliasOrId) {
    if (active && (active.alias === aliasOrId || active.id === aliasOrId)) {
      active.cancelled = true;
      return true;
    }
    for (const job of pending) {
      if (job.alias === aliasOrId || job.id === aliasOrId) {
        job.cancelled = true;
        return true;
      }
    }
    return false;
  }

  async function runActive() {
    while (active) {
      const job = active;
      if (job.cancelled) {
        job.settle(encodeClosedError("internal_failure"));
        promoteNext();
        continue;
      }
      job.startedAt = now();
      let result;
      try {
        result = await executeJob(job);
      } catch {
        result = encodeClosedError("internal_failure");
      }
      if (job.cancelled) {
        // No late success after cancel.
        job.settle(encodeClosedError("internal_failure"));
      } else {
        job.settle(result);
      }
      promoteNext();
    }
  }

  function promoteNext() {
    active = null;
    while (pending.length > 0) {
      const next = pending.shift();
      if (next.cancelled) {
        next.settle(encodeClosedError("internal_failure"));
        continue;
      }
      active = next;
      return;
    }
  }

  async function executeJob(job) {
    if (terminated) {
      return encodeClosedError("internal_failure");
    }

    const requestObj = {
      jsonrpc: "2.0",
      id: job.id,
      method: "tools/call",
      params: {
        name: job.method,
        arguments: job.args,
      },
    };
    const frame = Buffer.from(`${canonicalJsonString(requestObj)}\n`, "utf8");
    if (frame.length > MAX_REQUEST_BYTES) {
      return encodeClosedError("invalid_request");
    }

    try {
      roles.stdin.write(frame);
    } catch (err) {
      if (err && err.code === "queue_overflow") {
        return encodeClosedError("invalid_request");
      }
      terminated = true;
      return encodeClosedError("internal_failure");
    }
    // Do not drain here: the injected fake transport consumes live stdin
    // bytes. writeTrace remains immutable evidence; capacity resets on drain.

    const deadlineAt = job.startedAt + DEADLINE_MS;
    let responseBytes = null;

    while (now() <= deadlineAt) {
      if (job.cancelled) {
        roles.stdout.drain();
        return encodeClosedError("internal_failure");
      }
      const parsedEvent = parseClosedNextEvent(
        nextEvent(handle),
        sessionReadySeen,
      );
      if (parsedEvent.error) {
        terminated = true;
        roles.stdout.drain();
        return encodeClosedError("internal_failure");
      }
      if (parsedEvent.kind === "ready") {
        sessionReadySeen = true;
        continue;
      }
      if (parsedEvent.kind === "hang") {
        await idleYield();
        continue;
      }
      if (parsedEvent.kind === "exit") {
        terminated = true;
        roles.stdout.drain();
        // Child died before a complete matched response — not success.
        return encodeClosedError("internal_failure");
      }
      if (parsedEvent.kind === "stderr") {
        continue;
      }
      if (parsedEvent.kind === "stdout") {
        const chunk = parsedEvent.bytes;
        if (chunk.length === 0) continue;
        try {
          roles.stdout.push(chunk);
        } catch {
          terminated = true;
          roles.stdout.drain();
          return encodeClosedError("response_too_large");
        }
        const buffered = roles.stdout.peekAll();
        if (buffered.length > MAX_RESPONSE_BYTES) {
          terminated = true;
          roles.stdout.drain();
          return encodeClosedError("response_too_large");
        }
        const nl = buffered.indexOf(0x0a);
        if (nl === -1) {
          // Partial frame — keep waiting until deadline or more bytes.
          continue;
        }
        // One newline-terminated response plus trailing bytes is desync.
        if (nl !== buffered.length - 1) {
          terminated = true;
          roles.stdout.drain();
          return encodeClosedError("internal_failure");
        }
        responseBytes = Buffer.from(buffered.subarray(0, nl));
        // Consume the completed line from the queue (resets output frame cap).
        roles.stdout.drain();
        break;
      }
      terminated = true;
      roles.stdout.drain();
      return encodeClosedError("internal_failure");
    }

    if (job.cancelled) {
      roles.stdout.drain();
      return encodeClosedError("internal_failure");
    }
    if (responseBytes === null) {
      // Timeout / incomplete — no automatic retry; reset output frame accounting.
      roles.stdout.drain();
      return encodeClosedError("internal_failure");
    }
    if (responseBytes.length > MAX_RESPONSE_BYTES) {
      return encodeClosedError("response_too_large");
    }

    let parsed;
    try {
      parsed = JSON.parse(responseBytes.toString("utf8"));
    } catch {
      terminated = true;
      return encodeClosedError("internal_failure");
    }
    if (!parsed || typeof parsed !== "object" || parsed.jsonrpc !== "2.0") {
      terminated = true;
      return encodeClosedError("internal_failure");
    }
    if (parsed.id !== job.id) {
      terminated = true;
      return encodeClosedError("internal_failure");
    }
    if (Object.prototype.hasOwnProperty.call(parsed, "error")) {
      // Transport-level JSON-RPC error — closed failure, no retry.
      return encodeClosedError("internal_failure");
    }
    const result = parsed.result;
    if (!result || typeof result !== "object" || !Array.isArray(result.content)) {
      terminated = true;
      return encodeClosedError("internal_failure");
    }
    const textPart = result.content.find(
      (c) => c && c.type === "text" && typeof c.text === "string",
    );
    if (!textPart) {
      terminated = true;
      return encodeClosedError("internal_failure");
    }
    // Return raw canonical strict-server response bytes unchanged in a
    // standard tool-result content block (preserves instruction_authority:"none").
    const raw = textPart.text;
    if (Buffer.byteLength(raw, "utf8") > MAX_RESPONSE_BYTES) {
      return encodeClosedError("response_too_large");
    }
    return toolResultBlock(raw, { isError: result.isError === true });
  }

  return {
    handle,
    launchTuple,
    fdRoles: roles,
    invokeAlias,
    cancel,
    get terminated() {
      return terminated;
    },
    markTerminated() {
      terminated = true;
    },
  };
}

export default {
  register,
  activate,
  RUNTIME_NOT_QUALIFIED,
  TOOL_ALIASES,
  MCP_METHODS,
  validateLaunchTuple,
  createConnectorSession,
  createStrictFdRoles,
  computeLaunchPayloadSha256,
  canonicalJsonBytes,
  sha256Labeled,
  closedErrorPayload,
};
