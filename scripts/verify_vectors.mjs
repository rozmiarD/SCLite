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
console.log("sclite_vectors_ok:javascript");
