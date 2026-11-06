# ADR-0019: Datasheets are referenced by exact revision, never committed

- Status: Accepted
- Date: 2026-11-06

## Context

The new-driver checklist said to store the datasheet in `docs/datasheet/` "where its licence allows", while the
driver template, the pull-request template and the agents page say no vendor PDF is committed. Vendor licences
rarely allow redistribution and change over time, and a repository cannot tell which licence applied when a file
was added. What reviewers and auditors actually need is to know exactly which revision the code was written
against.

## Decision

- No datasheet, reference manual or application note is committed to a Kokeb Labs repository.
  `tracked-files/datasheets` fails CI on a tracked PDF under `docs/` that is listed as vendor documentation.
- Each driver lists the documents it was written against in `docs/datasheets.yml`: vendor, title, document
  number, revision, date, the vendor's URL, and the SHA-256 of the PDF that was used. The hash lets anyone confirm
  they hold the same revision without the repository redistributing it.
- Code comments cite a datasheet by document number, revision and section (KB-CPP-111).

## Consequences

- The new-driver checklist and rule KB-DOC-035 change to the reference model.
- For a safety-level component the list is part of the evidence package: it identifies the source of every
  register value and timing in the requirements.
