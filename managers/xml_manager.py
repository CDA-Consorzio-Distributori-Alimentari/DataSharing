from datetime import datetime
import calendar
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from numbers import Number
import os
import re
from pathlib import Path

import pandas as pd
from lxml import etree

from services.data_sharing_config import Option


class XMLManager:

    _XSLT_NAMESPACE = {"xsl": "http://www.w3.org/1999/XSL/Transform"}

    def __init__(self, config=None):
        self.config = config
        self.last_output_file = None

    def _build_output_directory(self, socio, option: Option):
        output_dir = os.path.join(self.config.output_path, str(socio).strip(), option.code)
        os.makedirs(output_dir, exist_ok=True)
        return output_dir

    def _save_xml(self, xml_content, option: Option, socio):
        output_dir = self._build_output_directory(socio, option)

        current_datetime = datetime.now()
        placeholders = {key: current_datetime.strftime(fmt) for key, fmt in self.config.placeholders.items()}

        naming_convention = option.naming_convention
        for placeholder, value in placeholders.items():
            naming_convention = naming_convention.replace(placeholder, value)

        if not naming_convention.lower().endswith(".xml"):
            naming_convention = f"{naming_convention}.xml"

        full_path = os.path.join(output_dir, naming_convention)
        if os.path.exists(full_path):
            os.remove(full_path)

        with open(full_path, "w", encoding="utf-8") as file:
            file.write(xml_content)

        self.last_output_file = full_path
        return full_path

    def _to_text(self, value):
        if pd.isna(value):
            return ""
        return str(value).strip()

    def _pick_column(self, data: pd.DataFrame, *candidates):
        for name in candidates:
            if name in data.columns:
                return name
        return None

    def _get_cell(self, row, *candidates):
        for name in candidates:
            if name in row.index:
                return row.get(name)
        return None

    def _normalize_name(self, value: str):
        return re.sub(r"[^a-z0-9]", "", value.lower())

    def _resolve_template_path(self, option: Option) -> str:
        template_path = getattr(option, "xslt_template", None)
        template_root = Path(self.config.template_path)
        if template_path:
            if os.path.isabs(template_path):
                return template_path

            configured_template_path = Path(template_path)
            if configured_template_path.parent != Path("."):
                return str((template_root / configured_template_path).resolve(strict=False))

            candidate_paths = [
                (template_root / option.code / configured_template_path.name).resolve(strict=False),
                (template_root / configured_template_path.name).resolve(strict=False),
            ]
            for candidate_path in candidate_paths:
                if candidate_path.exists():
                    return str(candidate_path)

            return str(candidate_paths[0])

        candidates = []
        preferred_root = (template_root / option.code).resolve(strict=False)
        search_roots = []
        if preferred_root.exists():
            search_roots.append(preferred_root)
        search_roots.append(template_root)

        visited_roots = set()
        for search_root in search_roots:
            normalized_root = str(search_root)
            if normalized_root in visited_roots:
                continue
            visited_roots.add(normalized_root)

            for root_dir, dir_names, file_names in os.walk(search_root):
                dir_names[:] = [name for name in dir_names if name.lower() != "old"]
                for file_name in file_names:
                    if not file_name.lower().endswith(".xslt"):
                        continue
                    full_path = os.path.join(root_dir, file_name)
                    candidates.append((full_path, self._normalize_name(file_name)))

        if not candidates:
            raise FileNotFoundError(f"Nessun file XSLT trovato nella cartella template: {template_root}")

        option_keys = [
            self._normalize_name(getattr(option, "name", "")),
            self._normalize_name(getattr(option, "code", "")),
        ]
        option_keys = [key for key in option_keys if key]
        ranked = []
        for full_path, normalized_name in candidates:
            score = 0
            for key in option_keys:
                if key in normalized_name:
                    score += len(key)
            ranked.append((score, full_path))

        ranked.sort(key=lambda item: (-item[0], item[1]))
        if ranked[0][0] <= 0:
            raise FileNotFoundError(
                f"Nessun template XSLT determinabile automaticamente per il data sharing {getattr(option, 'code', 'sconosciuto')}"
            )
        return ranked[0][1]

    def _set_text(self, parent, tag: str, value):
        element = etree.SubElement(parent, tag)
        text_value = self._to_text(value)
        if text_value:
            element.text = text_value
        return element

    def _resolve_candidates(self, row, candidates):
        if not candidates:
            return None
        if isinstance(candidates, str):
            candidates = [candidates]
        for name in candidates:
            if name in row.index:
                return row.get(name)
        return None

    def _resolve_special_value(self, row, special_mapping):
        if isinstance(special_mapping, str):
            return self._get_cell(row, special_mapping)
        if isinstance(special_mapping, list):
            return self._resolve_candidates(row, special_mapping)
        if isinstance(special_mapping, dict):
            fields = special_mapping.get("fields", [])
            if fields:
                separator = special_mapping.get("separator", "")
                values = [self._to_text(self._get_cell(row, field_name)) for field_name in fields]
                values = [value for value in values if value]
                return separator.join(values)
            source = special_mapping.get("source")
            if source:
                return self._get_cell(row, source)
        return None

    def _resolve_field_value(self, row, field_name: str, special_mappings):
        if field_name in special_mappings:
            special_value = self._resolve_special_value(row, special_mappings[field_name])
            if special_value is not None:
                return special_value
        return self._get_cell(row, field_name)

    def _parse_template_select(self, select_expression: str):
        parts = [part.strip() for part in select_expression.split("/") if part.strip()]
        if len(parts) < 2:
            return None
        return {
            "path": "/".join(parts[-2:]),
            "container_tag": parts[-2],
            "item_tag": parts[-1],
            "match": parts[-1],
        }

    def _template_node(self, xslt_doc, match_name: str):
        template_nodes = xslt_doc.xpath(
            f"//xsl:template[@match='{match_name}']",
            namespaces=self._XSLT_NAMESPACE,
        )
        if not template_nodes:
            return None
        return template_nodes[0]

    def _extract_value_fields_from_template(self, template_node):
        fields = []
        for expression in template_node.xpath(".//xsl:value-of/@select", namespaces=self._XSLT_NAMESPACE):
            match = re.search(r"normalize-space\(([^)]+)\)", expression)
            candidate = match.group(1) if match else expression
            candidate = candidate.strip()
            if not candidate or "/" in candidate or candidate.startswith("@"):
                continue
            if candidate.startswith("./"):
                candidate = candidate[2:]
            if candidate not in fields:
                fields.append(candidate)
        return fields

    def _template_children(self, xslt_doc, template_node):
        children = []
        for select_expression in template_node.xpath(".//xsl:apply-templates/@select", namespaces=self._XSLT_NAMESPACE):
            child_section = self._parse_template_select(select_expression)
            if not child_section:
                continue
            child_template = self._template_node(xslt_doc, child_section["match"])
            if child_template is None:
                raise ValueError(f"Template XSLT mancante per la sezione {child_section['path']}")
            child_section["fields"] = self._extract_value_fields_from_template(child_template)
            child_section["children"] = []
            children.append(child_section)
        return children

    def _root_template(self, xslt_doc):
        root_templates = xslt_doc.xpath("//xsl:template[starts-with(@match, '/')]", namespaces=self._XSLT_NAMESPACE)
        if not root_templates:
            raise ValueError("Template XSLT non valido: manca il template radice.")
        return root_templates[0]

    def _root_source_tag(self, root_template):
        match_value = root_template.get("match", "").strip()
        if not match_value.startswith("/"):
            raise ValueError("Template XSLT non valido: il template radice deve matchare un elemento sorgente.")
        return match_value.lstrip("/")

    def _dataset_attributes(self, root_template):
        attributes = []
        for attribute_value in root_template.xpath(".//@*"):
            for attr_name in re.findall(r"\{@([^}]+)\}", attribute_value):
                if attr_name not in attributes:
                    attributes.append(attr_name)
        return attributes

    def _xslt_model(self, xslt_path: str):
        with open(xslt_path, "rb") as file:
            xslt_doc = etree.parse(file)

        root_template = self._root_template(xslt_doc)
        sections = []
        for select_expression in root_template.xpath(".//xsl:apply-templates/@select", namespaces=self._XSLT_NAMESPACE):
            section = self._parse_template_select(select_expression)
            if not section:
                continue
            template_node = self._template_node(xslt_doc, section["match"])
            if template_node is None:
                raise ValueError(f"Template XSLT mancante per la sezione {section['path']}")
            section["fields"] = self._extract_value_fields_from_template(template_node)
            section["children"] = self._template_children(xslt_doc, template_node)
            sections.append(section)

        if not sections:
            raise ValueError("Template XSLT non valido: nessuna sezione sorgente rilevata.")

        return {
            "root_tag": self._root_source_tag(root_template),
            "root_attributes": self._dataset_attributes(root_template),
            "sections": sections,
        }

    def _period_bounds(self, periodo: str):
        if len(periodo) != 6:
            raise ValueError("periodo deve essere nel formato YYYYMM")
        year = int(periodo[:4])
        month = int(periodo[4:])
        return {
            "DateFrom": datetime(year, month, 1).strftime("%Y-%m-%d"),
            "DateTo": datetime(year, month, calendar.monthrange(year, month)[1]).strftime("%Y-%m-%d"),
        }

    def _parse_decimal(self, value) -> Decimal:
        if pd.isna(value):
            return Decimal("0")
        raw = str(value).strip()
        if not raw:
            return Decimal("0")
        normalized = raw.replace(",", ".")
        try:
            return Decimal(normalized)
        except InvalidOperation:
            return Decimal("0")

    def _to_decimal_10_3(self, value) -> str:
        dec_value = self._parse_decimal(value)
        return format(dec_value.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP), "f")

    def _first_series_value(self, series: pd.Series):
        for value in series.tolist():
            if self._to_text(value):
                return value
        return None

    def _series_for_attribute(self, data: pd.DataFrame, attribute_name: str, special_mappings):
        if attribute_name in data.columns:
            return data[attribute_name]

        special_mapping = special_mappings.get(attribute_name)
        if isinstance(special_mapping, str) and special_mapping in data.columns:
            return data[special_mapping]
        if isinstance(special_mapping, list):
            column_name = self._pick_column(data, *special_mapping)
            if column_name:
                return data[column_name]
        if isinstance(special_mapping, dict):
            source = special_mapping.get("source")
            if source and source in data.columns:
                return data[source]
        return None

    def _resolve_dataset_attribute(self, attribute_name: str, data: pd.DataFrame, period_bounds, special_mappings):
        if attribute_name in period_bounds:
            return period_bounds[attribute_name]

        if attribute_name.endswith("Count"):
            return str(len(data))

        if attribute_name.startswith("Total"):
            base_name = attribute_name[len("Total"):]
            if not base_name:
                raise ValueError(f"Attributo {attribute_name} non risolvibile automaticamente.")
            series = self._series_for_attribute(data, base_name, special_mappings)
            if series is None:
                raise ValueError(
                    f"Attributo aggregato {attribute_name} non risolvibile. Definire {base_name} nella query o in xml_mapping."
                )
            total_value = sum((self._parse_decimal(value) for value in series), Decimal("0"))
            return self._to_decimal_10_3(total_value)

        series = self._series_for_attribute(data, attribute_name, special_mappings)
        if series is not None:
            return self._to_text(self._first_series_value(series))

        if data.empty:
            raise ValueError(
                f"Attributo dataset {attribute_name} non risolvibile con DataFrame vuoto. Definirlo in xml_mapping o nella query."
            )

        first_row = data.iloc[0]
        special_value = self._resolve_special_value(first_row, special_mappings.get(attribute_name))
        if special_value is not None:
            return self._to_text(special_value)

        raise ValueError(
            f"Attributo dataset {attribute_name} non risolvibile automaticamente. Definirlo nella query o in xml_mapping."
        )

    def _is_numeric_value(self, value):
        if pd.isna(value) or isinstance(value, bool):
            return False
        return isinstance(value, Number)

    def _is_integer_value(self, value):
        if not self._is_numeric_value(value):
            return False
        if isinstance(value, Decimal):
            return value == value.to_integral_value()
        if isinstance(value, float):
            return value.is_integer()
        return True

    def _infer_series_type(self, series: pd.Series):
        values = [value for value in series.tolist() if not pd.isna(value) and self._to_text(value)]
        if not values:
            return "string"
        if any(isinstance(value, str) for value in values):
            return "string"
        if all(self._is_integer_value(value) for value in values):
            return "integer"
        if all(self._is_numeric_value(value) for value in values):
            return "decimal_10_3"
        return "string"

    def _infer_record_types(self, records, field_names):
        if not field_names:
            return {}
        if not records:
            return {field_name: "string" for field_name in field_names}

        frame = pd.DataFrame(records)
        inferred_types = {}
        for field_name in field_names:
            if field_name not in frame.columns:
                inferred_types[field_name] = "string"
                continue
            inferred_types[field_name] = self._infer_series_type(frame[field_name])
        return inferred_types

    def _format_source_value(self, value, value_type: str):
        if value_type == "integer":
            if pd.isna(value):
                return ""
            return str(int(value))
        if value_type == "decimal_10_3":
            return self._to_decimal_10_3(value)
        return self._to_text(value)

    def _section_group_keys(self, option: Option, section, section_df: pd.DataFrame):
        grouping = getattr(option, "xml_grouping", None) or {}
        configured_keys = None
        for section_key in (section["path"], section["container_tag"], section["item_tag"]):
            if section_key in grouping:
                configured_keys = grouping[section_key]
                break

        if section.get("children"):
            if configured_keys is None:
                raise ValueError(f"Configurazione xml_grouping mancante per la sezione {section['path']}")
            resolved_keys = [key for key in configured_keys if key in section_df.columns]
            if not resolved_keys:
                raise ValueError(f"Nessuna chiave di grouping valida per la sezione {section['path']}")
            return resolved_keys

        if configured_keys is not None:
            resolved_keys = [key for key in configured_keys if key in section_df.columns]
            if resolved_keys:
                return resolved_keys

        return [key for key in section.get("fields", []) if key in section_df.columns]

    def _build_source_document(self, data: pd.DataFrame, option: Option, periodo: str) -> etree._Element:
        if data is None:
            data = pd.DataFrame()

        special_mappings = getattr(option, "xml_mapping", None) or {}
        xslt_path = self._resolve_template_path(option)
        xslt_model = self._xslt_model(xslt_path)
        period_bounds = self._period_bounds(periodo)

        root = etree.Element(xslt_model["root_tag"])
        for attribute_name in xslt_model["root_attributes"]:
            attribute_value = self._resolve_dataset_attribute(attribute_name, data, period_bounds, special_mappings)
            if attribute_value:
                root.set(attribute_name, attribute_value)

        section_records = {section["path"]: [] for section in xslt_model["sections"]}

        for _, row in data.iterrows():
            for section in xslt_model["sections"]:
                record = {
                    field_name: self._resolve_field_value(row, field_name, special_mappings)
                    for field_name in section.get("fields", [])
                }
                for child_section in section.get("children", []):
                    for field_name in child_section.get("fields", []):
                        record[field_name] = self._resolve_field_value(row, field_name, special_mappings)
                section_records[section["path"]].append(record)

        for section in xslt_model["sections"]:
            section_node = etree.SubElement(root, section["container_tag"])
            records = section_records.get(section["path"], [])
            section_fields = list(section.get("fields", []))
            child_sections = section.get("children", [])
            child_fields = []
            for child_section in child_sections:
                child_fields.extend(child_section.get("fields", []))

            section_df = pd.DataFrame(records) if records else pd.DataFrame(columns=section_fields + child_fields)
            section_field_types = self._infer_record_types(records, section_fields)
            child_field_types = {
                child_section["path"]: self._infer_record_types(records, child_section.get("fields", []))
                for child_section in child_sections
            }

            if not child_sections:
                dedup_columns = section_fields or list(section_df.columns)
                dedup_df = section_df[dedup_columns].drop_duplicates() if dedup_columns else section_df.drop_duplicates()
                for _, current_row in dedup_df.iterrows():
                    item_node = etree.SubElement(section_node, section["item_tag"])
                    for field_name in section_fields:
                        self._set_text(
                            item_node,
                            field_name,
                            self._format_source_value(current_row.get(field_name), section_field_types.get(field_name, "string")),
                        )
                continue

            group_keys = self._section_group_keys(option, section, section_df)
            grouped_rows = section_df.groupby(group_keys, dropna=False) if group_keys else [(None, section_df)]
            for _, group in grouped_rows:
                first_row = group.iloc[0]
                item_node = etree.SubElement(section_node, section["item_tag"])
                for field_name in section_fields:
                    self._set_text(
                        item_node,
                        field_name,
                        self._format_source_value(first_row.get(field_name), section_field_types.get(field_name, "string")),
                    )

                for child_section in child_sections:
                    child_container_node = etree.SubElement(item_node, child_section["container_tag"])
                    for _, detail_row in group.iterrows():
                        child_item_node = etree.SubElement(child_container_node, child_section["item_tag"])
                        for field_name in child_section.get("fields", []):
                            self._set_text(
                                child_item_node,
                                field_name,
                                self._format_source_value(
                                    detail_row.get(field_name),
                                    child_field_types.get(child_section["path"], {}).get(field_name, "string"),
                                ),
                            )

        return root

    def _transform_with_xslt(self, source_root: etree._Element, xslt_path: str) -> str:
        with open(xslt_path, "rb") as file:
            xslt_doc = etree.parse(file)
        transform = etree.XSLT(xslt_doc)
        result = transform(etree.ElementTree(source_root))
        return etree.tostring(result, pretty_print=True, xml_declaration=True, encoding="UTF-8").decode("utf-8")

    def _generate_clean_xml(self, data: pd.DataFrame, option: Option, periodo: str) -> str:
        source_root = self._build_source_document(data, option, periodo)
        xslt_path = self._resolve_template_path(option)
        return self._transform_with_xslt(source_root, xslt_path)

    def create_xml(self, db_content: pd.DataFrame, params: Option, periodo: str, socio):
        transformed_data = self._generate_clean_xml(db_content, params, periodo)
        self._save_xml(transformed_data, params, socio)
        return transformed_data
