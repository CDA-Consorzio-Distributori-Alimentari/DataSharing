<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <xsl:output method="xml" indent="yes" encoding="UTF-8"/>

    <xsl:template match="/DataSet">
        <Payload xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="wsdata CCH WHS.xsd" StructureVersion="1" WholesalerID="{@WholesalerID}">
            <Period TotalVolume="{@TotalVolume}" PeriodType="Month" DateFrom="{@DateFrom}" DateTo="{@DateTo}" TotalRecordsCount="{@TotalRecordsCount}">
                <Outlets>
                    <xsl:apply-templates select="Outlets/Outlet"/>
                </Outlets>
                <Sales TransactionType="Sales">
                    <xsl:apply-templates select="Sales/Transaction"/>
                </Sales>
                <Products>
                    <xsl:apply-templates select="Products/Product"/>
                </Products>
            </Period>
        </Payload>
    </xsl:template>

    <xsl:template match="Outlet">
        <OutletEntry>
            <DeliverTo>
                <OutletNumber>                   
                    <xsl:value-of select="normalize-space(CodiceClienteCDA)"/>                    
                </OutletNumber>
                <Name1>OSCURATO</Name1>
                <Name2 xsi:nil="true"/>
                <ContactPerson xsi:nil="true"/>
                <Address1 xsi:nil="true"/>
                <Address2 xsi:nil="true"/>
                <PostalCode>
                    <xsl:value-of select="normalize-space(Cap)"/>
                </PostalCode>
                <City>
                    <xsl:value-of select="normalize-space(Localita)"/>
                </City>
                <Telephone1 xsi:nil="true"/>
                <Telephone2 xsi:nil="true"/>
                <Fax xsi:nil="true"/>
                <Email xsi:nil="true"/>
                <VatNumber>
                    <xsl:value-of select="normalize-space(PartitaIva)"/>
                </VatNumber>
                <KeyAccount xsi:nil="true"/>
                <Channel>
                    <xsl:value-of select="normalize-space(SubCategoriaDescrizione)"/>
                </Channel>
                <OutletNumberHbc/>
            </DeliverTo>
            <BillTo>
                <OutletNumber>
                    <xsl:value-of select="normalize-space(CodiceClienteCDA)"/>
                </OutletNumber>
                <Name1>OSCURATO</Name1>
                <Name2 xsi:nil="true"/>
                <ContactPerson xsi:nil="true"/>
                <Address1 xsi:nil="true"/>
                <Address2 xsi:nil="true"/>
                <PostalCode>
                    <xsl:value-of select="normalize-space(Cap)"/>
                </PostalCode>
                <City>
                    <xsl:value-of select="normalize-space(Localita)"/>
                </City>
                <Telephone1 xsi:nil="true"/>
                <Telephone2 xsi:nil="true"/>
                <Fax xsi:nil="true"/>
                <Email xsi:nil="true"/>               
                <VatNumber xsi:nil="true"/>
                <KeyAccount xsi:nil="true"/>
                <Channel>
                    <xsl:value-of select="normalize-space(SubCategoriaDescrizione)"/>
                </Channel>
                <OutletNumberHbc/>
            </BillTo>
        </OutletEntry>
    </xsl:template>

    <xsl:template match="Transaction">
        <Transaction>
            <OutletNumber>
                <xsl:value-of select="normalize-space(CodiceClienteCDA)"/> 
            </OutletNumber>
            <DeliveryDate>
                <xsl:value-of select="normalize-space(DataDDT)"/>
            </DeliveryDate>
            <OrderNumberHbc/>
            <InvoiceNumber>
                <xsl:value-of select="normalize-space(NumeroDDT)"/>
            </InvoiceNumber>
            <xsl:apply-templates select="Details/Detail"/>
        </Transaction>
    </xsl:template>

    <xsl:template match="Detail">
        <TransactionDetails>
            <ProductNumber>
                <xsl:value-of select="normalize-space(ArticoliCodiceCDA)"/>
            </ProductNumber>
            <Quantity>
                <xsl:value-of select="normalize-space(Volume)"/>
            </Quantity>
            <Price xsi:nil="true"/>
        </TransactionDetails>
    </xsl:template>

    <xsl:template match="Product">
        <ProductEntry>
            <ProductNumber>
                <xsl:value-of select="normalize-space(ArticoliCodiceCDA)"/>
            </ProductNumber>
            <ProductName>
                <xsl:value-of select="normalize-space(ArticoliDescrizioneCDA)"/>
            </ProductName>
            <UnitOfQuantity>L</UnitOfQuantity>
            <ArticleNameHbc>
                <xsl:value-of select="normalize-space(ArticoliDescrizioneHbc)"/>            
            </ArticleNameHbc>
            <ArticleNumberHbc>
               <xsl:value-of select="normalize-space(ArticoliCodiceHbc)"/>
            </ArticleNumberHbc>
            <EanConsumerUnit xsi:nil="true"/>
            <EanMultipack xsi:nil="true"/>
            <EanTradeUnit xsi:nil="true"/>
            <ProductRemarks xsi:nil="true"/>
            <PurchasePrice xsi:nil="true"/>
            <PackageSizeLitres xsi:nil="true"/>
            <SalesUnit xsi:nil="true"/>
            <PackageType xsi:nil="true"/>
            <Subunits xsi:nil="true"/>
        </ProductEntry>
    </xsl:template>
</xsl:stylesheet>