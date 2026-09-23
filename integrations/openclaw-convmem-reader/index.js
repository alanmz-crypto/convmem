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
    clearTrace() {
      writeTrace.length = 0;
    },
    get byteLength() {
      return size;
    },
  };
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

  const caps = capabilityData && typeof capabilityData === "object" ? capabilityData : {};
  const pathCaps = caps.paths && typeof caps.paths === "object" ? caps.paths : null;
  if (pathCaps) {
    for (const [pathField, digestField] of PATH_DIGEST_FIELDS) {
      const path = manifest[pathField];
      const entry = pathCaps[path];
      if (!entry || typeof entry !== "object") {
        throw launchError(`capability_missing:${path}`);
      }
      if (entry.symlink === true) {
        throw launchError(`capability_symlink:${path}`);
      }
      if (entry.kind !== undefined && entry.kind !== "file" && entry.kind !== "tree") {
        throw launchError(`capability_kind:${path}`);
      }
      if (typeof entry.mode === "number") {
        // Public/runtime artifacts are read-only for the runtime role (no owner-write bit).
        if ((entry.mode & 0o222) !== 0) {
          throw launchError(`capability_writable:${path}`);
        }
      }
      if (entry.uid !== undefined && entry.uid !== 0 && entry.uid !== 1000) {
        // Operator/root ownership assumption only (virtual).
        throw launchError(`capability_uid:${path}`);
      }
      if (typeof entry.digest === "string" && entry.digest !== manifest[digestField]) {
        throw launchError(`capability_digest:${path}`);
      }
    }
    for (const dirField of ["working_directory", "service_home", "temp_directory"]) {
      const path = manifest[dirField];
      const entry = pathCaps[path];
      if (!entry) continue;
      if (entry.symlink === true) {
        throw launchError(`capability_symlink:${path}`);
      }
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

    const deadlineAt = job.startedAt + DEADLINE_MS;
    let responseBytes = null;
    let idlePolls = 0;

    while (now() <= deadlineAt) {
      if (job.cancelled) {
        return encodeClosedError("internal_failure");
      }
      const event = nextEvent(handle);
      if (!event || typeof event !== "object") {
        idlePolls += 1;
        await idleYield();
        if (idlePolls > 256 || now() > deadlineAt) break;
        continue;
      }
      idlePolls = 0;
      const kind = event.kind;
      if (kind === "ready") {
        continue;
      }
      if (kind === "hang") {
        await idleYield();
        if (typeof pollWait === "function") {
          idlePolls = 0;
        } else {
          idlePolls += 1;
        }
        if (idlePolls > 256 || now() > deadlineAt) break;
        continue;
      }
      if (kind === "exit") {
        terminated = true;
        // Child died before a complete matched response — not success.
        return encodeClosedError("internal_failure");
      }
      if (kind === "stderr") {
        continue;
      }
      if (kind === "stdout") {
        const chunk = decodeEventBytes(event);
        if (chunk.length === 0) continue;
        try {
          roles.stdout.push(chunk);
        } catch {
          terminated = true;
          return encodeClosedError("response_too_large");
        }
        const buffered = roles.stdout.peekAll();
        if (buffered.length > MAX_RESPONSE_BYTES) {
          terminated = true;
          return encodeClosedError("response_too_large");
        }
        const nl = buffered.indexOf(0x0a);
        if (nl === -1) {
          // Partial frame — keep waiting until deadline or more bytes.
          continue;
        }
        responseBytes = buffered.subarray(0, nl);
        // Consume the completed line from the queue.
        roles.stdout.drain();
        break;
      }
    }

    if (job.cancelled) {
      return encodeClosedError("internal_failure");
    }
    if (responseBytes === null) {
      // Timeout / incomplete — no automatic retry.
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

  function decodeEventBytes(event) {
    if (typeof event.bytes_b64 === "string" && event.bytes_b64.length > 0) {
      return Buffer.from(event.bytes_b64, "base64");
    }
    return Buffer.alloc(0);
  }

  return {
    handle,
    launchTuple,
    fdRoles: roles,
    invokeAlias,
    cancel,
    get terminated() {
      return terminated,
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
