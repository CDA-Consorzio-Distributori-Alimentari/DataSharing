from datetime import datetime
import calendar
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import os
from xml.sax.saxutils import escape

import pandas as pd
from lxml import etree

from data_sharing_config import Option


class XMLManager:

    def __init__(self, config=None):
        self.config = config

    def save_xml(self, xml_content, option: Option):
        output_dir = os.path.join(self.config._output_path, "xml")
        os.makedirs(output_dir, exist_ok=True)

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

    def _to_text(self, value):
        if pd.isna(value):
            return ""
        return escape(str(value).strip())

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

    def _outlet_number(self, row):
        codice = self._get_cell(row, "TI_Clienti_Codice")
        codice_pdc = self._get_cell(row, "TI_Clienti_Codice_Pdc")
        return f"{self._to_text(codice)}_{self._to_text(codice_pdc)}"

    def _pretty_xml(self, xml_content: str) -> str:
        parser = etree.XMLParser(remove_blank_text=True)
        root = etree.fromstring(xml_content.encode("utf-8"), parser)
        return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8").decode("utf-8")

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

    def generate_clean_xml(self, data: pd.DataFrame, periodo: str) -> str:
        if data is None:
            data = pd.DataFrame()

        required_columns = ["TI_Clienti_Codice", "TI_Clienti_Codice_Pdc"]
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            raise ValueError(f"Colonne mancanti per OutletNumber: {', '.join(missing_columns)}")

        if len(periodo) != 6:
            raise ValueError("periodo deve essere nel formato YYYYMM")

        year = int(periodo[:4])
        month = int(periodo[4:])
        date_from = datetime(year, month, 1).strftime("%Y-%m-%d")
        date_to = datetime(year, month, calendar.monthrange(year, month)[1]).strftime("%Y-%m-%d")

        total_records_count = len(data)
        quantity_col = self._pick_column(data, "TW_Vendite_Pezzi", "Quantity")
        quantity_series = data.get(quantity_col, pd.Series(dtype="object"))
        total_volume_raw = sum((self._parse_decimal(v) for v in quantity_series), Decimal("0"))
        total_volume = self._to_decimal_10_3(total_volume_raw)
        wholesaler_col = self._pick_column(data, "TC_Soci_CocaCola_Codice", "WholesalerID")
        wholesaler_id = self._to_text(data.iloc[0][wholesaler_col]) if not data.empty and wholesaler_col else ""

        outlets_columns = [
            "TI_Clienti_Codice", "TI_Clienti_Codice_Pdc", "Filiale", "TW_Clienti_Codice", "ClientiCodice", "NomeCliente", "TW_Clienti_Localita", "Localita",
            "TW_Clienti_Cap", "PostalCode", "TC_Soci_Codice", "SociCodice",
            "TC_Sub_Categoria_Descrizione", "SubCategoriaDescrizione"
        ]
        outlets_df = data[[c for c in outlets_columns if c in data.columns]].drop_duplicates() if not data.empty else pd.DataFrame()

        products_columns = ["ProductNumber", "TC_Articoli_Codice", "ProductName", "TC_Articoli_Descrizione", "ArticoliCodiceCocaCola"]
        products_df = data[[c for c in products_columns if c in data.columns]].drop_duplicates() if not data.empty else pd.DataFrame()

        outlets_parts = ["<Outlets>"]
        for _, row in outlets_df.iterrows():
            outlet_number = self._outlet_number(row)
            nome_cliente = self._to_text(self._get_cell(row, "NomeCliente"))
            localita = self._to_text(self._get_cell(row, "TW_Clienti_Localita", "Localita"))
            postal_code = self._to_text(self._get_cell(row, "TW_Clienti_Cap", "PostalCode"))
            key_account = self._to_text(self._get_cell(row, "TC_Soci_Codice", "SociCodice"))
            channel = self._to_text(self._get_cell(row, "TC_Sub_Categoria_Descrizione", "SubCategoriaDescrizione"))

            outlets_parts.append(
                "<OutletEntry>"
                "<DeliverTo>"
                f"<OutletNumber>{outlet_number}</OutletNumber>"
                f"<Name1>{nome_cliente}</Name1>"
                "<Name2 xsi:nil=\"true\"/>"
                "<ContactPerson xsi:nil=\"true\"/>"
                f"<Address1>{localita}</Address1>"
                "<Address2 xsi:nil=\"true\"/>"
                f"<PostalCode>{postal_code}</PostalCode>"
                f"<City>{localita}</City>"
                "<Telephone1 xsi:nil=\"true\"/>"
                "<Telephone2 xsi:nil=\"true\"/>"
                "<Fax xsi:nil=\"true\"/>"
                "<Email xsi:nil=\"true\"/>"
                "<VatNumber xsi:nil=\"true\"/>"
                f"<KeyAccount>{key_account}</KeyAccount>"
                f"<Channel>{channel}</Channel>"
                "<OutletNumberHbc></OutletNumberHbc>"
                "</DeliverTo>"
                "<BillTo>"
                f"<OutletNumber>{outlet_number}</OutletNumber>"
                f"<Name1>{nome_cliente}</Name1>"
                "<Name2 xsi:nil=\"true\"/>"
                "<ContactPerson xsi:nil=\"true\"/>"
                "<Address1 xsi:nil=\"true\"/>"
                "<Address2 xsi:nil=\"true\"/>"
                f"<PostalCode>{postal_code}</PostalCode>"
                f"<City>{localita}</City>"
                "<Telephone1 xsi:nil=\"true\"/>"
                "<Telephone2 xsi:nil=\"true\"/>"
                "<Fax xsi:nil=\"true\"/>"
                "<Email xsi:nil=\"true\"/>"
                "<VatNumber xsi:nil=\"true\"/>"
                "<KeyAccount xsi:nil=\"true\"/>"
                f"<Channel>{channel}</Channel>"
                "<OutletNumberHbc></OutletNumberHbc>"
                "</BillTo>"
                "</OutletEntry>"
            )
        outlets_parts.append("</Outlets>")
        outlets_xml = "".join(outlets_parts)

        sales_parts = ["<Sales TransactionType=\"Sales\">"]
        if not data.empty:
            invoice_col = self._pick_column(data, "TW_Vendite_Numero_DDT", "InvoiceNumber")
            delivery_col = self._pick_column(data, "DataDDT")
            product_col = self._pick_column(data, "ProductNumber", "TC_Articoli_Codice")
            group_keys = ["TI_Clienti_Codice", "TI_Clienti_Codice_Pdc", "Filiale", "TW_Clienti_Codice", "ClientiCodice", delivery_col, invoice_col]
            available_keys = [k for k in group_keys if k in data.columns]
            grouped_rows = data.groupby(available_keys, dropna=False) if available_keys else [(None, data)]

            for _, group in grouped_rows:
                first = group.iloc[0]
                sales_parts.append("<Transaction>")
                sales_parts.append(f"<OutletNumber>{self._outlet_number(first)}</OutletNumber>")
                sales_parts.append(f"<DeliveryDate>{self._to_text(first.get(delivery_col))}</DeliveryDate>")
                sales_parts.append("<OrderNumberHbc></OrderNumberHbc>")
                sales_parts.append(f"<InvoiceNumber>{self._to_text(first.get(invoice_col))}</InvoiceNumber>")

                for _, row in group.iterrows():
                    product_number = self._to_text(row.get(product_col))
                    quantity = self._to_decimal_10_3(row.get(quantity_col))
                    sales_parts.append(
                        "<TransactionDetails>"
                        f"<ProductNumber>{product_number}</ProductNumber>"
                        f"<Quantity>{quantity}</Quantity>"
                        "<Price xsi:nil=\"true\"/>"
                        "</TransactionDetails>"
                    )

                sales_parts.append("</Transaction>")
        sales_parts.append("</Sales>")
        sales_xml = "".join(sales_parts)

        products_parts = ["<Products>"]
        for _, row in products_df.iterrows():
            article_number_hbc = self._to_text(self._get_cell(row, "ArticoliCodiceCocaCola"))
            products_parts.append(
                "<ProductEntry>"
                f"<ProductNumber>{self._to_text(self._get_cell(row, 'ProductNumber', 'TC_Articoli_Codice'))}</ProductNumber>"
                f"<ProductName>{self._to_text(self._get_cell(row, 'ProductName', 'TC_Articoli_Descrizione'))}</ProductName>"
                "<UnitOfQuantity>L</UnitOfQuantity>"
                "<ArticleNameHbc></ArticleNameHbc>"
                f"<ArticleNumberHbc>{article_number_hbc}</ArticleNumberHbc>"
                "<EanConsumerUnit xsi:nil=\"true\"/>"
                "<EanMultipack xsi:nil=\"true\"/>"
                "<EanTradeUnit xsi:nil=\"true\"/>"
                "<ProductRemarks xsi:nil=\"true\"/>"
                "<PurchasePrice xsi:nil=\"true\"/>"
                "<PackageSizeLitres xsi:nil=\"true\"/>"
                "<SalesUnit xsi:nil=\"true\"/>"
                "<PackageType xsi:nil=\"true\"/>"
                "<Subunits xsi:nil=\"true\"/>"
                "</ProductEntry>"
            )
        products_parts.append("</Products>")
        products_xml = "".join(products_parts)

        final_xml = (
            f"<Payload xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" "
            f"xsi:noNamespaceSchemaLocation=\"wsdata CCH WHS.xsd\" StructureVersion=\"1\" "
            f"WholesalerID=\"{wholesaler_id}\">"
            f"<Period TotalVolume=\"{total_volume}\" PeriodType=\"Month\" DateFrom=\"{date_from}\" "
            f"DateTo=\"{date_to}\" TotalRecordsCount=\"{total_records_count}\">"
            f"{outlets_xml}{sales_xml}{products_xml}"
            "</Period>"
            "</Payload>"
        )

        return self._pretty_xml(final_xml)

    def create_xml(self, db_content: pd.DataFrame, params: Option, periodo: str):
        transformed_data = self.generate_clean_xml(db_content, periodo)
        self.save_xml(transformed_data, params)
        return transformed_data

    def create(self, db_content: pd.DataFrame, params: Option, periodo: str):
        return self.create_xml(db_content, params, periodo)