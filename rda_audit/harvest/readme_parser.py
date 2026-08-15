import re

from ..common import DOI_RE

CITE_HEADING_RE = re.compile(
    r"^(#{1,6})\s*.*\b(citing|citation[s]?|how to cite|cite (?:this|us|the))\b.*$",
    re.IGNORECASE | re.MULTILINE,
)
BIB_START_RE = re.compile(
    r"@(article|misc|software|inproceedings|book|techreport|manual|"
    r"phdthesis|mastersthesis|inbook)\s*\{", re.IGNORECASE)
BIB_KEY_RE = re.compile(r"\b(title|author|year|doi|version)\s*=\s*", re.IGNORECASE)

def _match_braces(text, open_idx):
    depth = 0
    for j in range(open_idx, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return j
    return -1


def _extract_bibtex_entry(text):
    m = BIB_START_RE.search(text)
    if not m:
        return None
    open_idx = text.index("{", m.start())
    close = _match_braces(text, open_idx)
    return text[m.start():close + 1] if close != -1 else None


def _bib_fields(entry):
    out = {}
    for m in BIB_KEY_RE.finditer(entry):
        key = m.group(1).lower()
        i = m.end()
        if i >= len(entry):
            continue
        c = entry[i]
        if c == "{":
            j = _match_braces(entry, i)
            val = entry[i + 1:j] if j != -1 else ""
        elif c == '"':
            j = entry.find('"', i + 1)
            val = entry[i + 1:j] if j != -1 else ""
        else:
            m2 = re.match(r"[^,\n}]+", entry[i:])
            val = m2.group(0) if m2 else ""
        val = re.sub(r"[{}]", "", val).strip()
        if val and key not in out:
            out[key] = val
    return out

def extract_citation_section(text):
    """Return the text from a 'Citing/Citation/How to cite' heading to the next
    heading of the same-or-higher level, or None."""
    m = CITE_HEADING_RE.search(text)
    if not m:
        return None
    level = len(m.group(1))
    after = text[m.end():]
    nxt = re.search(rf"^#{{1,{level}}}\s", after, re.MULTILINE)
    section = after[: nxt.start()] if nxt else after
    return section.strip()[:5000]  # cap: some READMEs are enormous

def extract_bibtex_fields(text):
    """First BibTeX entry in text -> field dict. Brace-matching extraction:
    handles one-line entries, closing braces on field lines, nested/protective
    braces, quoted and bare values, and @ characters inside the entry."""
    entry = _extract_bibtex_entry(text)
    if not entry:
        return None
    fields = _bib_fields(entry)
    if not fields:
        return None
    fields["_raw"] = entry[:3000]
    return fields

def find_dois(text):
    seen, out = set(), []
    for d in DOI_RE.findall(text):
        d = d.rstrip(".,;:")
        if d.lower() not in seen:
            seen.add(d.lower())
            out.append(d)
    return out


def parse_readme(text):
    section = extract_citation_section(text)
    scope = section if section else text
    return {
        "has_citation_section": section is not None,
        "citation_section": section,
        "bibtex": extract_bibtex_fields(scope) or extract_bibtex_fields(text),
        "dois_in_citation_section": find_dois(section) if section else [],
        "dois_anywhere": find_dois(text)[:20],
    }

if __name__ == "__main__":
    demo = """# CoolSim
Fast simulations.
## How to Cite
Please cite our paper (doi:10.5281/zenodo.1234567):
```
@article{cool2024, title={CoolSim: Fast Things}, author={Ada Lovelace and Grace Hopper},
year={2024}, doi={10.1000/xyz123},
}
```
## License
MIT
"""
    import json
    print(json.dumps(parse_readme(demo), indent=2))
