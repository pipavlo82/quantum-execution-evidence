# Provenance

This repository is a **new Git root**, not a fork and not a continuation of another Git history.

The implementation was extracted from a locally reviewed Quantum Execution Evidence lane that lived inside a separate Verifiable Composition prototype. The source project was pinned at commit:

`7e2830c9fe0b30b6b2db9417ebe02b282a57787a`

The reviewed pre-extraction checker SHA-256 was:

`d13bda9e710d6d70f43b2e9fdb3ecee6f3d99e06c777d38c57c8094d7fc16789`

The reviewed pre-extraction experiment source-lock SHA-256 was:

`562b9e79a1f64e173215f8f9f82594e9a6d297a6634d734b8e6724f1d28e8e03`.Extraction was performed from a read-only seed snapshot whose complete manifest was independently checked before repository construction. The standalone package changes import/layout and source-lock mechanics so it has no runtime dependency on the former composition project or on machine-specific absolute paths.

This provenance statement does **not** claim that every standalone file is byte-identical to the former lane. Corpus request/package bytes and their manifest semantics were preserved; standalone code and documentation were deliberately adapted for independent execution.

The only copied executable upstream dependency is the minimal byte-pinned Semantic ABI linker surface under `vendor/semantic-abi/`. Its original license files are retained.No QPU, provider API, private key, paid compute, external runtime service, RVR adapter, ReceiptOS capsule producer, TSEI engine, RSI adapter, Chronicle admission, RE4CTOR entropy source, or PQ verifier is embedded or invoked by this provenance boundary.

Expectation authorship remains `SAME_TASK_AUTHOR_NOT_INDEPENDENT`. Source hashes prove byte identity, not authorship independence or semantic correctness.

## RVR v0 primitive vendoring

Native RVR profile work vendors three exact files from RVR commit `549a7e150ddc75df88dc90ee93f331fea7464567`: the upstream license, independent Python adapter, and generic Verification Profile Manifest schema. The adapter SHA-256 is `03505efc8ee993f118fad2c71f706870d25de0da61a393a1f18f7b310bded235`.

The QEV-specific Verification Profile, schema, vectors, expected results, and mutation witnesses are authored in this repository. They do not alter the vendored RVR bytes.
