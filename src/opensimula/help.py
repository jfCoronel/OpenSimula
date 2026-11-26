"""Help of the components for the app: the descriptions of their parameters and
variables, and the links to them in the documentation.

The descriptions are written once, in the component pages of the documentation
(``mkdocs/component_list_*.md``), as list items under ``### <type>`` and its
``#### Parameters`` and ``#### Variables``::

    - **volume_flow** [_math_exp_, unit = "l/h", default = "0"]: Hot water used...
    - __Q_sensible__ [W]: Sensible heat supplied by the system...
    - **T_mains** (°C), **T_supply** (°C): Mains water temperature and...

The same reader is used by the mkdocs hook ``mkdocs_hooks.py``, which gives each of
those items an anchor (``dhw_demand-volume_flow``, ``hvac_dx_system-var-q_sensible``),
and by ``python -m opensimula.help mkdocs``, which writes ``help.json``, shipped with
the package: the editor and the results viewer show the description as a tooltip and
link to the anchor.
"""

import html
import json
import pathlib
import re
import sys

DOCS_URL = "https://opensimula.jfcoronel.org/"
HELP_FILE = pathlib.Path(__file__).parent / "help.json"
COMMON = "__common__"  # the parameters every component has (name, type, description)

_NAME = re.compile(r"(\*\*|__)(.+?)\1")
_SEPARATOR = re.compile(r"\s*(,|\.\.\.|…|and|/)?\s*")


def _slug(text):
    return re.sub(r"[^a-z0-9_]+", "-", text.lower()).strip("-")


def parameter_anchor(type_name, name):
    """Anchor of a parameter in the documentation, e.g. ``dhw_demand-volume_flow``."""
    prefix = "common" if type_name == COMMON else type_name
    return f"{_slug(prefix)}-{_slug(name)}"


def variable_anchor(type_name, name):
    """Anchor of a variable in the documentation, e.g. ``dhw_demand-var-q_demand``."""
    return f"{_slug(type_name)}-var-{_slug(name)}"


def _bracket(text, i):
    """End of a [...] or (...) group starting at i (nested ones too), or None."""
    pairs = {"[": "]", "(": ")"}
    if i >= len(text) or text[i] not in pairs:
        return None
    depth, quote = 0, False
    for j in range(i, len(text)):
        c = text[j]
        if c == '"':
            quote = not quote
        elif not quote and c in "[(":
            depth += 1
        elif not quote and c in "])":
            depth -= 1
            if depth == 0:
                return j + 1
    return None


def parse_item(line):
    """The names of a documentation list item and its description.

    Args:
        line (str): a line of a component page.

    Returns:
        tuple: ([(name, column of its opening ** or __, unit)], description), or
            None if the line is not a list item of that form.
    """
    if not line.startswith("- "):
        return None
    i, names = 2, []
    while True:
        m = _NAME.match(line, i)
        if not m:
            break
        start, i = m.start(), m.end()
        unit = ""
        while i < len(line) and line[i] == " ":
            i += 1
        end = _bracket(line, i)
        if end is not None:
            group = line[i + 1:end - 1]
            u = re.search(r'unit\s*=\s*"([^"]*)"', group)
            unit = u.group(1) if u else ("" if group.startswith("_") else group.strip())
            i = end
        # several names in one mark: __T_s0, T_s1__
        for name in m.group(2).split(","):
            names.append((html.unescape(name.strip()), start, unit))
        sep = _SEPARATOR.match(line, i)
        if sep and _NAME.match(line, sep.end()):
            i = sep.end()
            continue
        break
    if not names:
        return None
    rest = line[i:].lstrip()
    if not rest.startswith(":"):
        return None
    return names, rest[1:].strip()


def clean(text):
    """Description as plain text: no markdown marks, links or html."""
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)  # [text](link)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("**", "").replace("__", "").replace("`", "")
    text = re.sub(r"(?<!\w)_([^_\s][^_]*?)_(?!\w)", r"\1", text)  # _italic_
    return re.sub(r"\s+", " ", text).strip()


def parse_page(lines, types):
    """Walk the lines of a component page.

    Args:
        lines (list): lines of the page.
        types (set): component type names.

    Yields:
        tuple: (line index, type, "parameters" or "variables", names, description) of
            every documented item; type is ``COMMON`` for the common parameters.
    """
    type_name, section = None, None
    for n, line in enumerate(lines):
        if line.startswith("### "):
            title = line[4:].strip()
            type_name = title if title in types else (COMMON if title == "Common parameters" else None)
            section = "parameters" if type_name == COMMON else None
            continue
        if line.startswith("#### "):
            title = line[5:].strip().lower()
            section = ("parameters" if title.startswith("parameter")
                       else "variables" if title.startswith("variable") else None)
            continue
        if type_name is None or section is None:
            continue
        item = parse_item(line)
        if item:
            yield n, type_name, section, item[0], item[1]


def build(docs_dir, types=None):
    """The help of every component from the documentation.

    Args:
        docs_dir (str or pathlib.Path): the ``mkdocs`` folder.
        types (iterable, optional): component types; all the registered ones by default.

    Returns:
        dict: ``{"docs_url", "components": {type: {"page", "anchor", "parameters":
            {name: {"text", "unit", "anchor"}}, "variables": {...}}}, "common": {...}}``.
    """
    if types is None:
        from opensimula.editor.schema import component_types
        types = component_types()
    types = set(types)
    docs = pathlib.Path(docs_dir)
    components, common = {}, {}
    for path in sorted(docs.glob("component_list*.md")):
        page = path.stem + "/"
        lines = path.read_text(encoding="utf-8").splitlines()
        for line in lines:
            if line.startswith("### ") and line[4:].strip() in types:
                t = line[4:].strip()
                components[t] = {"page": page, "anchor": t.lower(), "parameters": {}, "variables": {}}
        for _, t, section, names, text in parse_page(lines, types):
            for name, _, unit in names:
                entry = {
                    "text": clean(text),
                    "unit": unit,
                    "anchor": (variable_anchor(t, name) if section == "variables"
                               else parameter_anchor(t, name)),
                    "page": page,
                }
                if t == COMMON:
                    common[name] = entry
                else:
                    components[t][section].setdefault(name, entry)
    return {"docs_url": DOCS_URL, "components": components, "common": common}


# _________________ What the app asks _________________

_help = None


def _data():
    global _help
    if _help is None:
        try:
            _help = json.loads(HELP_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _help = {"docs_url": DOCS_URL, "components": {}, "common": {}}
    return _help


def _url(page, anchor):
    return f"{_data().get('docs_url', DOCS_URL)}{page}#{anchor}"


def component_help(type_name):
    """Link to the documentation of a component type, None if not documented."""
    c = _data()["components"].get(type_name)
    return _url(c["page"], c["anchor"]) if c else None


def parameter_help(type_name, name):
    """Description and link of a parameter of a component type.

    Returns:
        tuple: (text, url), (None, None) if not documented.
    """
    data = _data()
    entry = data["components"].get(type_name, {}).get("parameters", {}).get(name)
    entry = entry or data["common"].get(name)
    return (entry["text"], _url(entry["page"], entry["anchor"])) if entry else (None, None)


def _name_pattern(documented):
    """Regular expression of a documented name with placeholders (``outside_<zone>``,
    ``T_node_1``, ``T_node_N``, ``Q_reheat_i``), None if it has none."""
    parts = re.split(r"<[^>]+>", documented)
    if len(parts) == 1:
        m = re.fullmatch(r"(.+_)(?:1|N|i|n)", documented)
        if not m:
            return None
        parts = [m.group(1), ""]
    return r"\w+".join(re.escape(p) for p in parts)


def variable_help(type_name, name):
    """Description and link of a variable of a component type. Variables with a number
    or the name of another component at the end (``T_node_3``, ``Q_reheat_2``,
    ``outside_office``) are found by their documented pattern (``T_node_1``,
    ``T_node_N``, ``Q_reheat_i``, ``outside_<zone>``).

    Returns:
        tuple: (text, url), (None, None) if not documented.
    """
    variables = _data()["components"].get(type_name, {}).get("variables", {})
    entry = variables.get(name)
    if entry is None:
        for documented, e in variables.items():
            pattern = _name_pattern(documented)
            if pattern and re.fullmatch(pattern, name):
                entry = e
                break
    return (entry["text"], _url(entry["page"], entry["anchor"])) if entry else (None, None)


def main(argv=None):
    """``python -m opensimula.help [mkdocs folder]``: write help.json."""
    argv = sys.argv[1:] if argv is None else argv
    docs = argv[0] if argv else "mkdocs"
    data = build(docs)
    HELP_FILE.write_text(json.dumps(data, indent=1, ensure_ascii=False, sort_keys=True) + "\n",
                         encoding="utf-8")
    n_par = sum(len(c["parameters"]) for c in data["components"].values())
    n_var = sum(len(c["variables"]) for c in data["components"].values())
    print(f"{HELP_FILE}: {len(data['components'])} components, {n_par} parameters, "
          f"{n_var} variables, {len(data['common'])} common parameters")


if __name__ == "__main__":
    main()
