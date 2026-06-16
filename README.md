# sysml-obfuscate

Obfuscate SysML v2 models for sharing sensitive data. Strips domain-specific
names, documentation, and quantity values while preserving the structural
relationships that define the architecture.

## Why

Cameo/MagicDraw support model obfuscation to redact sensitive details before
sharing with partners, customers, or training data pipelines. `sysml-obfuscate`
brings the same capability to SysML v2 textual models by:

- Replacing element names with convention-compliant placeholders
- Replacing `doc /* ... */` text with lorem ipsum
- Scrambling numeric quantity values (mass, time, voltage, etc.)

Generated names follow [sysml-style](https://github.com/mycr0ft/sysml-style)
conventions — `UpperCamelCase` for definitions, `lowerCamelCase` for usages,
and `Port` suffix for ports — so the obfuscated model still passes naming
lint checks.

## Requirements

- Python 3.10+
- [sysmlpy](https://github.com/mycr0ft/sysmlpy) — the SysML v2 Python library

## Usage

```bash
python sysml_obfuscate.py model.sysml -o model.obf.sysml --seed 42
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `input` | — | Path to the `.sysml` file |
| `-o, --output` | stdout | Write obfuscated model to file |
| `--seed` | `0` | Random seed for reproducible output |
| `--no-scramble-values` | — | Preserve original numeric values |
| `--show-mapping` | — | Print name mapping to stderr |
| `--mapping-file` | — | Write name mapping as JSON |

### Save the name mapping for later de-obfuscation

```bash
python sysml_obfuscate.py model.sysml \
    -o model.obf.sysml \
    --mapping-file mapping.json \
    --show-mapping
```

## What gets transformed

| Element | Transformation | Example |
|---------|---------------|---------|
| Package name | `DroneModel` → `Pkg0000` |
| Part/item/action def | `Battery` → `Obj0000` |
| Part/item usage | `battery` → `obj0000` |
| Port def | `PowerOutPort` → `PowerPort` |
| Port usage | `supply` → `pwrPort` |
| Attribute def | `Capacity` → `Attr_0000` |
| Attribute usage | `capacity` → `attr0000` |
| `doc /* ... */` | Replaced with lorem ipsum |
| Quantity values | `1500 [kg]` → `2183.5 [kg]` |

## What stays the same

- Structural relationships (composition, specialization, connections)
- Type hierarchy and multiplicities
- Import statements and library references
- Connectivity (all `connect` paths are preserved with renamed endpoints)
- Multiplicity constraints (`[4]`, `[0..1]`, etc.)
