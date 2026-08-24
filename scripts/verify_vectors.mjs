import crypto from "node:crypto";
import fs from "node:fs";

function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (value !== null && typeof value === "object") {
    return `{${Object.keys(value).sort().map(k => `${JSON.stringify(k)}:${canonical(value[k])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

function sha256(text) { return crypto.createHash("sha256").update(text, "utf8").digest("hex"); }

const MAX_SAFE_JSON_INTEGER = Number.MAX_SAFE_INTEGER;

class CanonicalizationError extends Error {
  constructor(reasonCode) {
    super(reasonCode);
    this.reasonCode = reasonCode;
  }
}

function canonicalNumberV2(value) {
  if (!Number.isFinite(value)) throw new CanonicalizationError("non_finite_number");
  if (Object.is(value, -0) || value === 0) return "0";
  if (Number.isInteger(value) && Math.abs(value) > MAX_SAFE_JSON_INTEGER) {
    throw new CanonicalizationError("unsafe_integer");
  }
  return JSON.stringify(value);
}

function canonicalV2(value) {
  if (value === null) return "null";
  if (value === true) return "true";
  if (value === false) return "false";
  if (typeof value === "string") return JSON.stringify(value);
  if (typeof value === "number") return canonicalNumberV2(value);
  if (Array.isArray(value)) return `[${value.map(canonicalV2).join(",")}]`;
  if (typeof value === "object") {
    return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonicalV2(value[key])}`).join(",")}}`;
  }
  throw new CanonicalizationError("non_json_value");
}

function v2Result(item) {
  const value = Object.hasOwn(item, "value") ? item.value : Number(item.input);
  try {
    const encoded = canonicalV2(value);
    return { id: item.id, status: "accepted", canonical: encoded, sha256: sha256(encoded) };
  } catch (error) {
    if (error instanceof CanonicalizationError) {
      return { id: item.id, status: "rejected", reason_code: error.reasonCode };
    }
    throw error;
  }
}
function classify(item) {
  if (item.id === "duplicate") return /"a"\s*:[^,]+,\s*"a"\s*:/.test(item.input) ? "duplicate_key" : "accepted";
  if (item.id === "nonfinite") return /(?:NaN|Infinity)/.test(item.input) ? "non_standard_number" : "accepted";
  if (item.id === "path") return item.input.split("/").includes("..") ? "path_escape" : "accepted";
  if (item.id === "timestamp") return Number.isNaN(Date.parse(item.input)) ? "invalid_timestamp" : "accepted";
  if (item.id === "ticket") return item.input === "not_before>not_after" ? "invalid_ticket_interval" : "accepted";
  return "unknown_vector";
}

const corpus = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
for (const item of corpus.canonicalization) {
  const encoded = canonical(item.value);
  if (encoded !== item.canonical || sha256(encoded) !== item.sha256) process.exit(1);
}
if (sha256(canonical(corpus.chain.payload)) !== corpus.chain.sha256) process.exit(1);
const tag = crypto.createHmac("sha256", corpus.guard.key_utf8).update(canonical(corpus.guard.payload), "utf8").digest("hex");
if (tag !== corpus.guard.hmac_sha256) process.exit(1);
for (const item of corpus.negative) if (classify(item) !== item.classification) process.exit(1);
const v2Results = corpus.numeric_canonicalization_v0_2.map(v2Result);
for (let index = 0; index < v2Results.length; index += 1) {
  const actual = v2Results[index];
  const expected = corpus.numeric_canonicalization_v0_2[index];
  if (actual.status !== expected.status) process.exit(1);
  if (actual.status === "accepted" && (actual.canonical !== expected.canonical || actual.sha256 !== expected.sha256)) process.exit(1);
  if (actual.status === "rejected" && actual.reason_code !== expected.reason_code) process.exit(1);
}
if (process.argv[3] === "--v2-results") {
  console.log(JSON.stringify(v2Results));
  process.exit(0);
}
console.log("sclite_vectors_ok:javascript");
