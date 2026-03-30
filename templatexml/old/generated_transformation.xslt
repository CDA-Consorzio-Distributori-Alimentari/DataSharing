<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:ns="http://example.com/namespace">
    <xsl:output method="xml" indent="yes"/>
  <!-- Payload and Period elements corrected and moved to the top -->
    <ns:Payload xsi:noNamespaceSchemaLocation="wsdata CCH WHS.xsd" StructureVersion="{StructureVersion}" WholesalerID="{WholesalerID}">
        <ns:Period TotalVolume="{TotalVolume}" PeriodType="{PeriodType}" DateFrom="{DateFrom}" DateTo="{DateTo}" TotalRecordsCount="{TotalRecordsCount}"/>
    </ns:Payload>
    
    <!-- Template principale -->
    <xsl:template match="/">
        <TransformedPayload>
            <xsl:apply-templates select="Payload/Outlets/OutletEntry"/>
            <xsl:apply-templates select="Payload/Products/ProductEntry"/>
        </TransformedPayload>
    </xsl:template>

    <!-- Trasformazione per ogni OutletEntry -->
    <xsl:template match="OutletEntry">
        <Outlet>
            <DeliverTo>
                <OutletNumber><xsl:value-of select="DeliverTo/OutletNumber"/></OutletNumber>
                <OutletNumberHbc><xsl:value-of select="DeliverTo/OutletNumberHbc"/></OutletNumberHbc>
                <Name><xsl:value-of select="DeliverTo/Name1"/></Name>
                <Address><xsl:value-of select="DeliverTo/Address1"/></Address>
                <City><xsl:value-of select="DeliverTo/City"/></City>
                <PostalCode><xsl:value-of select="DeliverTo/PostalCode"/></PostalCode>
                <Channel><xsl:value-of select="DeliverTo/Channel"/></Channel>
                <KeyAccount><xsl:value-of select="DeliverTo/KeyAccount"/></KeyAccount>
                <VatNumber><xsl:value-of select="DeliverTo/VatNumber"/></VatNumber>
                <ContactPerson><xsl:value-of select="DeliverTo/ContactPerson"/></ContactPerson>
                <Telephone1><xsl:value-of select="DeliverTo/Telephone1"/></Telephone1>
                <Telephone2><xsl:value-of select="DeliverTo/Telephone2"/></Telephone2>
                <Fax><xsl:value-of select="DeliverTo/Fax"/></Fax>
                <Email><xsl:value-of select="DeliverTo/Email"/></Email>
            </DeliverTo>
            <BillTo>
                <OutletNumber><xsl:value-of select="BillTo/OutletNumber"/></OutletNumber>
                <OutletNumberHbc><xsl:value-of select="BillTo/OutletNumberHbc"/></OutletNumberHbc>
                <Name><xsl:value-of select="BillTo/Name1"/></Name>
                <Address><xsl:value-of select="BillTo/Address1"/></Address>
                <City><xsl:value-of select="BillTo/City"/></City>
                <PostalCode><xsl:value-of select="BillTo/PostalCode"/></PostalCode>
                <Channel><xsl:value-of select="BillTo/Channel"/></Channel>
                <KeyAccount><xsl:value-of select="BillTo/KeyAccount"/></KeyAccount>
                <VatNumber><xsl:value-of select="BillTo/VatNumber"/></VatNumber>
                <ContactPerson><xsl:value-of select="BillTo/ContactPerson"/></ContactPerson>
                <Telephone1><xsl:value-of select="BillTo/Telephone1"/></Telephone1>
                <Telephone2><xsl:value-of select="BillTo/Telephone2"/></Telephone2>
                <Fax><xsl:value-of select="BillTo/Fax"/></Fax>
                <Email><xsl:value-of select="BillTo/Email"/></Email>
            </BillTo>
        </Outlet>
    </xsl:template>

    <!-- Trasformazione per ogni ProductEntry -->
    <xsl:template match="ProductEntry">
        <Product>
            <ProductNumber><xsl:value-of select="ProductNumber"/></ProductNumber>
            <ProductName><xsl:value-of select="ProductName"/></ProductName>
            <UnitOfQuantity><xsl:value-of select="UnitOfQuantity"/></UnitOfQuantity>
            <ArticleNameHbc><xsl:value-of select="ArticleNameHbc"/></ArticleNameHbc>
            <ArticleNumberHbc><xsl:value-of select="ArticleNumberHbc"/></ArticleNumberHbc>
            <EanConsumerUnit><xsl:value-of select="EanConsumerUnit"/></EanConsumerUnit>
            <EanMultipack><xsl:value-of select="EanMultipack"/></EanMultipack>
            <EanTradeUnit><xsl:value-of select="EanTradeUnit"/></EanTradeUnit>
            <ProductRemarks><xsl:value-of select="ProductRemarks"/></ProductRemarks>
            <PurchasePrice><xsl:value-of select="PurchasePrice"/></PurchasePrice>
            <PackageSizeLitres><xsl:value-of select="PackageSizeLitres"/></PackageSizeLitres>
            <SalesUnit><xsl:value-of select="SalesUnit"/></SalesUnit>
            <PackageType><xsl:value-of select="PackageType"/></PackageType>
            <Subunits><xsl:value-of select="Subunits"/></Subunits>
        </Product>
    </xsl:template>

    <!-- Trasformazione per ogni Transaction -->
    <xsl:template match="Transaction">
        <Transaction>
            <OutletNumber><xsl:value-of select="OutletNumber"/></OutletNumber>
            <DeliveryDate><xsl:value-of select="DeliveryDate"/></DeliveryDate>
            <OrderNumberHbc><xsl:value-of select="OrderNumberHbc"/></OrderNumberHbc>
            <InvoiceNumber><xsl:value-of select="InvoiceNumber"/></InvoiceNumber>
            <xsl:for-each select="TransactionDetails">
                <TransactionDetails>
                    <ProductNumber><xsl:value-of select="ProductNumber"/></ProductNumber>
                    <Quantity><xsl:value-of select="Quantity"/></Quantity>
                    <Price><xsl:value-of select="Price"/></Price>
                </TransactionDetails>
            </xsl:for-each>
        </Transaction>
    </xsl:template>

  
</xsl:stylesheet>