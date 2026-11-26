"""mkdocs hooks (``hooks`` in mkdocs.yml).

Anchors for the help links of the app: every documented parameter and variable of the
component pages gets an anchor, ``<type>-<parameter>`` or ``<type>-var-<variable>``,
read by the same code that writes the help of the app (``opensimula.help``), so that
the links of the editor and the results viewer land on it.
"""

from opensimula import help as osm_help


def on_page_markdown(markdown, page, config, files):
    if not page.file.src_path.startswith("component_list"):
        return markdown
    from opensimula.editor.schema import component_types

    lines = markdown.split("\n")
    for n, type_name, section, names, _ in osm_help.parse_page(lines, set(component_types())):
        anchor = osm_help.variable_anchor if section == "variables" else osm_help.parameter_anchor
        ids = []
        for name, _, _ in names:
            a = anchor(type_name, name)
            if a not in ids:
                ids.append(a)
        tags = "".join(f'<a id="{a}" class="osm-anchor"></a>' for a in ids)
        lines[n] = "- " + tags + lines[n][2:]
    return "\n".join(lines)
