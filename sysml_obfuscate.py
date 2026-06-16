#!/usr/bin/env python3
"""sysml-obfuscate — Obfuscate SysML v2 models for sharing.

Replaces element names, documentation, and quantity values
while preserving structural relationships. Generated names
follow sysml-style conventions (UpperCamelCase for definitions,
lowerCamelCase for usages, Port suffix for ports).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import random
from pathlib import Path


# ---------------------------------------------------------------------------
# Deterministic name generator
# ---------------------------------------------------------------------------

class NameGenerator:
    """Generates unique obfuscated names following sysml-style conventions."""

    PORT_DEFS = [
        "PowerPort", "SignalPort", "ControlPort", "DataPort",
        "FlowPort", "BusPort", "ThermalPort", "PneumaticPort",
        "HydraulicPort", "OpticalPort",
    ]

    PORT_USAGES = [
        "pwrPort", "sigPort", "ctrlPort", "dataPort",
        "flowPort", "busPort", "thrmPort", "pneuPort",
        "hydrPort", "optPort",
    ]

    PORT_DEF_TMPL = "PortDef_{:04d}"
    PORT_USAGE_TMPL = "portDef{:04d}"

    TEMPLATES = {
        "package":      "Pkg{:04d}",
        "definition":   "Obj{:04d}",
        "usage":        "obj{:04d}",
        "port_def":     PORT_DEFS,
        "port_usage":   PORT_USAGES,
        "attr_def":     "Attr_{:04d}",
        "attr_usage":   "attr{:04d}",
    }

    def __init__(self, seed: int = 0):
        self._counters: dict[str, int] = {
            k: 0 for k in self.TEMPLATES if isinstance(self.TEMPLATES[k], str)
        }
        self._port_def_idx = 0
        self._port_usage_idx = 0
        self._port_def_fallback_counter = 0
        self._port_usage_fallback_counter = 0
        self._seen: dict[str, str] = {}
        self._used: set[str] = set()
        random.seed(seed)

    def _next(self, kind: str) -> str:
        template = self.TEMPLATES[kind]
        if isinstance(template, str):
            while True:
                name = template.format(self._counters[kind])
                self._counters[kind] += 1
                if name not in self._used:
                    self._used.add(name)
                    return name
        else:
            # Try the named list first
            is_def = kind == "port_def"
            idx = self._port_def_idx if is_def else self._port_usage_idx
            fallback_counter = (
                self._port_def_fallback_counter if is_def
                else self._port_usage_fallback_counter
            )
            fallback_tmpl = self.PORT_DEF_TMPL if is_def else self.PORT_USAGE_TMPL

            for candidate in template[idx:]:
                if is_def:
                    self._port_def_idx += 1
                else:
                    self._port_usage_idx += 1
                if candidate not in self._used:
                    self._used.add(candidate)
                    return candidate

            # Fall back to counter-based names
            while True:
                name = fallback_tmpl.format(fallback_counter)
                if is_def:
                    self._port_def_fallback_counter = fallback_counter + 1
                else:
                    self._port_usage_fallback_counter = fallback_counter + 1
                if name not in self._used:
                    self._used.add(name)
                    return name

    def obfuscate(self, original: str, sysml_type: str, is_definition: bool = False) -> str:
        if not original or self._is_uuid(original):
            original = "__unnamed__"

        if original in self._seen:
            return self._seen[original]

        kind = self._kind(sysml_type, is_definition)
        name = self._next(kind)
        self._seen[original] = name
        return name

    def _kind(self, sysml_type: str, is_definition: bool) -> str:
        if sysml_type == "package":
            return "package"
        if sysml_type == "port":
            return "port_def" if is_definition else "port_usage"
        if sysml_type == "attribute":
            return "attr_def" if is_definition else "attr_usage"
        return "definition" if is_definition else "usage"

    @staticmethod
    def _is_uuid(s: str) -> bool:
        if not isinstance(s, str) or len(s) != 36:
            return False
        parts = s.split("-")
        if len(parts) != 5:
            return False
        lengths = [8, 4, 4, 4, 12]
        return all(
            len(p) == n and all(c in "0123456789abcdef" for c in p.lower())
            for p, n in zip(parts, lengths)
        )

    @property
    def mapping(self) -> dict[str, str]:
        return dict(self._seen)


# ---------------------------------------------------------------------------
# Lorem ipsum for doc strings
# ---------------------------------------------------------------------------

_LOREM = (
    "Lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod "
    "tempor incididunt ut labore et dolore magna aliqua"
).split()


def _lorem_sentence(rng: random.Random) -> str:
    length = rng.randint(5, 15)
    words = [rng.choice(_LOREM) for _ in range(length)]
    sentence = " ".join(words)
    return sentence[0].upper() + sentence[1:] + "."


# ---------------------------------------------------------------------------
# Obfuscator
# ---------------------------------------------------------------------------

class SysMLObfuscator:
    """Main obfuscator that walks a sysmlpy model and transforms it."""

    def __init__(self, seed: int = 0, scramble_values: bool = True):
        self.rng = random.Random(seed)
        self.name_gen = NameGenerator(seed=seed)
        self.scramble_values = scramble_values

    @staticmethod
    def _is_definition(elem) -> bool:
        grammar = getattr(elem, "grammar", None)
        if grammar is not None and type(grammar).__name__.endswith("Definition"):
            return True
        is_def = getattr(elem, "is_definition", None)
        if is_def is not None:
            return is_def
        return False

    def _rename_element(self, elem):
        stype = getattr(elem, "sysml_type", None)
        is_def = self._is_definition(elem)
        name = getattr(elem, "name", None)
        if name:
            new_name = self.name_gen.obfuscate(name, stype, is_def)
            if hasattr(elem, "set_name"):
                try:
                    elem.set_name(new_name)
                except AttributeError:
                    elem.name = new_name
            else:
                elem.name = new_name

    def obfuscate_model(self, model) -> str:
        """Walk a sysmlpy Model, rename all elements, return obfuscated text."""
        for pkg in model.children:
            self._obfuscate_tree(pkg)
        return model.dump()

    def _obfuscate_tree(self, elem):
        self._rename_element(elem)
        if hasattr(elem, "children"):
            for child in list(elem.children):
                self._obfuscate_tree(child)

    def obfuscate_text(self, text: str, mapping: dict[str, str]) -> str:
        """Apply text-level transformations not available in the model API."""
        lines = text.split("\n")
        result: list[str] = []

        for line in lines:
            line = self._scramble_doc_comment(line)
            if self.scramble_values:
                line = self._scramble_numeric_values(line)
            result.append(line)

        text = "\n".join(result)

        # Replace references to renamed elements in the text
        for orig, new in sorted(mapping.items(), key=lambda x: -len(x[0])):
            text = re.sub(rf'\b{re.escape(orig)}\b', new, text)

        return text

    def _scramble_doc_comment(self, line: str) -> str:
        m = re.search(r"(doc\s*/\*)(.*?)(\*/)", line)
        if m:
            return line[: m.start(2)] + " " + _lorem_sentence(self.rng) + " " + line[m.end(2) :]
        return line

    def _scramble_numeric_values(self, line: str) -> str:
        def _replace_value(m: re.Match) -> str:
            prefix = m.group(1)
            num_str = m.group(2)
            unit = m.group(3) or ""
            try:
                val = float(num_str)
            except ValueError:
                return m.group(0)

            factor = 0.5 + self.rng.random() * 1.5
            offset = self.rng.uniform(-val * 0.1, val * 0.1)
            new_val = round(val * factor + offset, max(0, 6 - len(str(int(val)))))
            new_val = int(new_val) if new_val == int(new_val) else new_val
            return f"{prefix}{new_val}{unit}"

        return re.sub(r"(=\s*)(\d+(?:\.\d+)?)(\s*\[[^\]]*\])?", _replace_value, line)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Obfuscate SysML v2 models for sharing sensitive data.",
    )
    parser.add_argument("input", type=str, help="Input .sysml file")
    parser.add_argument("-o", "--output", type=str, help="Output file (default: stdout)")
    parser.add_argument("--seed", type=int, default=0, help="Random seed for reproducibility")
    parser.add_argument(
        "--no-scramble-values",
        action="store_false",
        dest="scramble_values",
        help="Skip scrambling of numeric quantity values",
    )
    parser.add_argument(
        "--show-mapping",
        action="store_true",
        help="Print the original→obfuscated name mapping",
    )
    parser.add_argument(
        "--mapping-file",
        type=str,
        help="Write the name mapping to a JSON file",
    )
    args = parser.parse_args()

    source = Path(args.input).read_text()

    sys.path.insert(0, str(Path.home() / "sysmlpy" / "src"))
    try:
        import sysmlpy
    except ImportError:
        print("Error: sysmlpy is required. See https://github.com/mycr0ft/sysmlpy", file=sys.stderr)
        sys.exit(1)

    obf = SysMLObfuscator(seed=args.seed, scramble_values=args.scramble_values)

    try:
        model = sysmlpy.loads(source)
    except Exception as e:
        print(f"Error parsing: {e}", file=sys.stderr)
        sys.exit(1)

    renamed = obf.obfuscate_model(model)
    result = obf.obfuscate_text(renamed, obf.name_gen.mapping)

    if args.show_mapping:
        print("// Name mapping:", file=sys.stderr)
        for orig, new in sorted(obf.name_gen.mapping.items()):
            print(f"//   {orig} -> {new}", file=sys.stderr)

    if args.mapping_file:
        Path(args.mapping_file).write_text(
            json.dumps(obf.name_gen.mapping, indent=2)
        )

    if args.output:
        Path(args.output).write_text(result)
    else:
        print(result)


if __name__ == "__main__":
    main()
