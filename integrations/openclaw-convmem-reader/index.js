/**
 * OpenClaw ConvMem reader plugin — ordinary production registration refuses
 * with runtime_not_qualified before any OS effect (Architecture §6.5.8).
 */

export const RUNTIME_NOT_QUALIFIED = "runtime_not_qualified";

export function register() {
  const err = new Error(RUNTIME_NOT_QUALIFIED);
  err.code = "runtime_not_qualified";
  err.exitCode = 78;
  throw err;
}

export function activate() {
  return register();
}

export default { register, activate, RUNTIME_NOT_QUALIFIED };
