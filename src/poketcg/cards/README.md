# cards

Static English card metadata concerns only.

This package owns:

- loading `EN_Card_Data.csv`,
- normalizing denormalized source rows into one card record per card id,
- validating source integrity,
- indexing metadata for fast read access,
- exposing typed query APIs for the rest of the system.

This package must remain free of:

- gameplay logic,
- observation parsing,
- strategy,
- search,
- training code.
