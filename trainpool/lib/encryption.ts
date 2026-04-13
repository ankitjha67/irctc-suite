/**
 * Per-trip AES-256-GCM encryption for ID proof numbers.
 *
 * Key derivation: HKDF-SHA256(master_secret, salt=trip_slug, info="trainpool-id-v1") → 32-byte key
 * Envelope: 12-byte IV || ciphertext || 16-byte auth tag
 *
 * Why per-trip keys: if one trip's key is ever compromised (unlikely given HKDF chain),
 * the blast radius is exactly one trip, not the whole database.
 */

import {
  createCipheriv,
  createDecipheriv,
  randomBytes,
  hkdfSync,
} from "node:crypto";

const MASTER_SECRET = process.env.TRIP_ENCRYPTION_SECRET;
if (!MASTER_SECRET || MASTER_SECRET.length < 32) {
  throw new Error(
    "TRIP_ENCRYPTION_SECRET must be set and at least 32 characters"
  );
}

const ALGO = "aes-256-gcm";
const IV_LEN = 12;
const TAG_LEN = 16;
const KEY_INFO = Buffer.from("trainpool-id-v1");

function deriveTripKey(tripSlug: string): Buffer {
  // HKDF-SHA256 → 32-byte key, scoped to this trip's slug
  const salt = Buffer.from(tripSlug, "utf8");
  const ikm = Buffer.from(MASTER_SECRET!, "utf8");
  const okm = hkdfSync("sha256", ikm, salt, KEY_INFO, 32);
  return Buffer.from(okm);
}

export function encryptIdNumber(
  plaintext: string,
  tripSlug: string
): { encrypted: Buffer; hint: string } {
  const key = deriveTripKey(tripSlug);
  const iv = randomBytes(IV_LEN);
  const cipher = createCipheriv(ALGO, key, iv);

  const ct = Buffer.concat([
    cipher.update(plaintext, "utf8"),
    cipher.final(),
  ]);
  const tag = cipher.getAuthTag();

  // Envelope: iv || ciphertext || tag
  const envelope = Buffer.concat([iv, ct, tag]);

  // Hint: last 4 chars for organizer dashboard display (never decrypted)
  const hint = plaintext.length >= 4
    ? "*".repeat(Math.max(0, plaintext.length - 4)) + plaintext.slice(-4)
    : "****";

  return { encrypted: envelope, hint };
}

export function decryptIdNumber(envelope: Buffer, tripSlug: string): string {
  if (envelope.length < IV_LEN + TAG_LEN) {
    throw new Error("Invalid ciphertext envelope");
  }
  const key = deriveTripKey(tripSlug);
  const iv = envelope.subarray(0, IV_LEN);
  const tag = envelope.subarray(envelope.length - TAG_LEN);
  const ct = envelope.subarray(IV_LEN, envelope.length - TAG_LEN);

  const decipher = createDecipheriv(ALGO, key, iv);
  decipher.setAuthTag(tag);
  const pt = Buffer.concat([decipher.update(ct), decipher.final()]);
  return pt.toString("utf8");
}

// Edit-token hashing: we never store raw edit tokens
import { createHash } from "node:crypto";
export function hashEditToken(token: string): string {
  return createHash("sha256").update(token).digest("hex");
}

export function generateEditToken(): string {
  return randomBytes(24).toString("base64url");
}
