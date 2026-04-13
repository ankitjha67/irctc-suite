/**
 * Paste-block generator — the core value prop.
 *
 * IRCTC's passenger details form, when pasted into, accepts tab-separated rows.
 * This module takes the decrypted passenger list and produces two outputs:
 *   1. tsv  — tab-separated, newline per passenger, ready to paste
 *   2. pretty — human-readable aligned table for the organizer to sanity-check
 *
 * IMPORTANT: This runs only on the server side. Raw ID numbers are decrypted
 * here on-demand, used to produce the block, and NEVER stored as a derived artifact.
 */

import { decryptIdNumber } from "./encryption";

export type PassengerRow = {
  full_name: string;
  age: number;
  gender: "M" | "F" | "T";
  berth_preference: string | null; // LB/MB/UB/SL/SU/NP
  id_type: string | null;
  id_number_encrypted: Buffer | null;
};

const GENDER_LABEL: Record<string, string> = { M: "Male", F: "Female", T: "Trans" };
const BERTH_LABEL: Record<string, string> = {
  LB: "Lower",
  MB: "Middle",
  UB: "Upper",
  SL: "Side Lower",
  SU: "Side Upper",
  NP: "No Preference",
};

export type BlockResult = {
  tsv: string;        // for the Copy button
  pretty: string;     // for visual preview in the modal
  row_count: number;
  warnings: string[]; // e.g., "Passenger #3 missing ID proof"
};

export function generateBlock(
  passengers: PassengerRow[],
  tripSlug: string,
  opts: { idProofRequired: boolean }
): BlockResult {
  const warnings: string[] = [];

  if (passengers.length === 0) {
    return {
      tsv: "",
      pretty: "No passengers yet.",
      row_count: 0,
      warnings: ["No passengers have joined this trip"],
    };
  }

  // Decrypt ID numbers on the fly, only in memory
  const rows = passengers.map((p, idx) => {
    let idNumber = "";
    if (p.id_number_encrypted) {
      try {
        idNumber = decryptIdNumber(p.id_number_encrypted, tripSlug);
      } catch {
        warnings.push(`Passenger #${idx + 1}: failed to decrypt ID number`);
      }
    } else if (opts.idProofRequired) {
      warnings.push(`Passenger #${idx + 1} (${p.full_name}): missing required ID proof`);
    }

    return {
      name: p.full_name,
      age: String(p.age),
      gender: GENDER_LABEL[p.gender] ?? p.gender,
      berth: p.berth_preference ? BERTH_LABEL[p.berth_preference] ?? p.berth_preference : "",
      idType: p.id_type ?? "",
      idNumber,
    };
  });

  // TSV format (IRCTC paste format)
  const tsvHeader = ["Name", "Age", "Gender", "Berth", "ID Type", "ID Number"].join("\t");
  const tsvRows = rows.map((r) =>
    [r.name, r.age, r.gender, r.berth, r.idType, r.idNumber].join("\t")
  );
  const tsv = [tsvHeader, ...tsvRows].join("\n");

  // Pretty format (visual check)
  const col = (s: string, w: number) => s.padEnd(w).slice(0, w);
  const prettyHeader = [
    col("Name", 24),
    col("Age", 4),
    col("Gender", 8),
    col("Berth", 14),
    col("ID", 12),
    col("Number", 20),
  ].join(" | ");
  const prettyRows = rows.map((r) =>
    [
      col(r.name, 24),
      col(r.age, 4),
      col(r.gender, 8),
      col(r.berth, 14),
      col(r.idType, 12),
      col(r.idNumber, 20),
    ].join(" | ")
  );
  const pretty = [prettyHeader, "-".repeat(prettyHeader.length), ...prettyRows].join("\n");

  return {
    tsv,
    pretty,
    row_count: rows.length,
    warnings,
  };
}

// Input validation for the passenger form
export function validatePassengerInput(input: unknown): {
  ok: boolean;
  errors: string[];
} {
  const errors: string[] = [];
  if (!input || typeof input !== "object") {
    return { ok: false, errors: ["Invalid payload"] };
  }
  const p = input as Record<string, unknown>;

  if (!p.full_name || typeof p.full_name !== "string" || p.full_name.trim().length < 2) {
    errors.push("Full name is required (min 2 chars)");
  }
  if (typeof p.full_name === "string" && p.full_name.length > 80) {
    errors.push("Full name too long (max 80 chars)");
  }

  const age = Number(p.age);
  if (!Number.isInteger(age) || age < 1 || age > 120) {
    errors.push("Age must be a whole number between 1 and 120");
  }

  if (p.gender !== "M" && p.gender !== "F" && p.gender !== "T") {
    errors.push("Gender must be M, F, or T");
  }

  if (p.berth_preference && !["LB", "MB", "UB", "SL", "SU", "NP"].includes(p.berth_preference as string)) {
    errors.push("Invalid berth preference");
  }

  if (p.id_type && !["AADHAAR", "PAN", "DL", "PASSPORT", "VOTER"].includes(p.id_type as string)) {
    errors.push("Invalid ID type");
  }

  if (p.id_number && typeof p.id_number === "string") {
    if (p.id_number.length < 4 || p.id_number.length > 32) {
      errors.push("ID number length looks wrong");
    }
  }

  return { ok: errors.length === 0, errors };
}
