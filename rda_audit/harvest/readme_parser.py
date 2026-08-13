import re

from ..common import DOI_RE

CITE_HEADING_RE = re.compile(
    r"^(#{1,6})\s*.*\b(citing|citation[s]?|how to cite|cite (?:this|us|the))\b.*$",
    re.IGNORECASE | re.MULTILINE,
)
BIBTEX_RE = re.compile(r"@(?:article|misc|software|inproceedings|book|techreport)\s*\{[^@]*?\n\}", re.DOTALL | re.IGNORECASE)
BIB_FIELD_RE = re.compile(r"\b(title|author|year|doi|version)\s*=\s*[{\"]([^{}\"]+)[}\"]",
                          re.IGNORECASE)

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
    m = BIBTEX_RE.search(text)
    if not m:
        return None
    fields = {}
    for k, v in BIB_FIELD_RE.findall(m.group(0)):
        fields.setdefault(k.lower(), re.sub(r"[{}]", "", v).strip())
    fields["_raw"] = m.group(0)[:3000]
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
