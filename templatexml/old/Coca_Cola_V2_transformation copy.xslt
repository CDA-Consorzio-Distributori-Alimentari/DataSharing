<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:output method="xml" indent="yes"/>

    <!-- Template for transforming data -->
    <xsl:template match="/">
        <Payload xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="wsdata CCH WHS.xsd" StructureVersion="1" WholesalerID="{@ID}">
            <Period TotalVolume="{TotalVolume}" PeriodType="Month" DateFrom="{DateFrom}" DateTo="{DateTo}" TotalRecordsCount="{TotalRecordsCount}">
                <Outlets>
                    <xsl:for-each select="Data/Outlets/Outlet">
                        <OutletEntry>
                            <DeliverTo>
                                <OutletNumber><xsl:value-of select="OutletNumber"/></OutletNumber>
                                <Name1><xsl:value-of select="Name1"/></Name1>
                                <Name2 xsi:nil="true"/>
                                <ContactPerson xsi:nil="true"/>
                                <Address1 xsi:nil="true"/>
                                <Address2 xsi:nil="true"/>
                                <PostalCode><xsl:value-of select="PostalCode"/></PostalCode>
                                <City><xsl:value-of select="City"/></City>
                                <Telephone1 xsi:nil="true"/>
                                <Telephone2 xsi:nil="true"/>
                                <Fax xsi:nil="true"/>
                                <Email xsi:nil="true"/>
                                <VatNumber xsi:nil="true"/>
                                <KeyAccount xsi:nil="true"/>
                                <Channel><xsl:value-of select="Channel"/></Channel>
                                <OutletNumberHbc xsi:nil="true"/>
                            </DeliverTo>
                            <BillTo>
                                <OutletNumber><xsl:value-of select="OutletNumber"/></OutletNumber>
                                <Name1><xsl:value-of select="Name1"/></Name1>
                                <Name2 xsi:nil="true"/>
                                <ContactPerson xsi:nil="true"/>
                                <Address1 xsi:nil="true"/>
                                <Address2 xsi:nil="true"/>
                                <PostalCode><xsl:value-of select="PostalCode"/></PostalCode>
                                <City><xsl:value-of select="City"/></City>
                                <Telephone1 xsi:nil="true"/>
                                <Telephone2 xsi:nil="true"/>
                                <Fax xsi:nil="true"/>
                                <Email xsi:nil="true"/>
                                <VatNumber xsi:nil="true"/>
                                <KeyAccount xsi:nil="true"/>
                                <Channel><xsl:value-of select="Channel"/></Channel>
                                <OutletNumberHbc xsi:nil="true"/>
                            </BillTo>
                        </OutletEntry>
                    </xsl:for-each>
                </Outlets>
                <Sales TransactionType="Sales">
                    <xsl:for-each select="Data/Sales/Transaction">
                        <Transaction>
                            <OutletNumber><xsl:value-of select="OutletNumber"/></OutletNumber>
                            <DeliveryDate><xsl:value-of select="DeliveryDate"/></DeliveryDate>
                            <InvoiceNumber><xsl:value-of select="InvoiceNumber"/></InvoiceNumber>
                            <TransactionDetails>
                                <xsl:for-each select="Details">
                                    <Detail>
                                        <ProductNumber><xsl:value-of select="ProductNumber"/></ProductNumber>
                                        <ProductName><xsl:value-of select="ProductName"/></ProductName>
                                        <UnitOfQuantity>L</UnitOfQuantity>
                                        <ArticleNameHbc><xsl:value-of select="ArticleNameHbc"/></ArticleNameHbc>
                                        <ArticleNumberHbc><xsl:value-of select="ArticleNumberHbc"/></ArticleNumberHbc>
                                        <EanConsumerUnit xsi:nil="true"/>
                                        <EanMultipack xsi:nil="true"/>
                                        <EanTradeUnit xsi:nil="true"/>
                                        <ProductRemarks xsi:nil="true"/>
                                        <PurchasePrice xsi:nil="true"/>
                                        <PackageSizeLitres xsi:nil="true"/>
                                        <SalesUnit xsi:nil="true"/>
                                        <PackageType xsi:nil="true"/>
                                        <Subunits xsi:nil="true"/>
                                        <Quantity><xsl:value-of select="Quantity"/></Quantity>
                                    </Detail>
                                </xsl:for-each>
                            </TransactionDetails>
                        </Transaction>
                    </xsl:for-each>
                </Sales>
            </Period>
        </Payload>
    </xsl:template>
</xsl:stylesheet>