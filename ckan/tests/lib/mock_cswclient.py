from ckan.lib.cswclient import GeoNetworkClient

class MockGeoNetworkClient(GeoNetworkClient):

    get_capabilities_request_xml = """<?xml version="1.0"?>
<csw:GetCapabilities xmlns:csw="http://www.opengis.net/cat/csw/2.0.2" service="CSW">
    <ows:AcceptVersions xmlns:ows="http://www.opengis.net/ows">
        <ows:Version>2.0.2</ows:Version>
    </ows:AcceptVersions>
    <ows:AcceptFormats xmlns:ows="http://www.opengis.net/ows">
        <ows:OutputFormat>application/xml</ows:OutputFormat>
    </ows:AcceptFormats>
</csw:GetCapabilities>"""

    get_capabilities_response_xml = """
<?xml version="1.0" encoding="UTF-8"?>
<csw:Capabilities xmlns:csw="http://www.opengis.net/cat/csw/2.0.2" xmlns:gml="http://www.opengis.net/gml" xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:ows="http://www.opengis.net/ows" xmlns:ogc="http://www.opengis.net/ogc" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="2.0.2" xsi:schemaLocation="http://www.opengis.net/cat/csw/2.0.2 http://schemas.opengis.net/csw/2.0.2/CSW-discovery.xsd">
  <ows:ServiceIdentification>
    <ows:Title />
    <ows:Abstract />
    <ows:Keywords>
      <!-- Keywords are automatically added by GeoNetwork
            according to catalogue content. -->
      <ows:Type>theme</ows:Type>
    </ows:Keywords>
    <ows:ServiceType>CSW</ows:ServiceType>
    <ows:ServiceTypeVersion>2.0.2</ows:ServiceTypeVersion>
    <ows:Fees />
    <ows:AccessConstraints />
  </ows:ServiceIdentification>
  <ows:ServiceProvider>
    <ows:ProviderName>GeoNetwork opensource</ows:ProviderName>
    <ows:ProviderSite xlink:href="http://localhost:8080/geonetwork" />
    <ows:ServiceContact>
      <ows:IndividualName />
      <ows:PositionName />
      <ows:ContactInfo>
        <ows:Phone>
          <ows:Voice />
          <ows:Facsimile />
        </ows:Phone>
        <ows:Address>
          <ows:DeliveryPoint />
          <ows:City />
          <ows:AdministrativeArea />
          <ows:PostalCode />
          <ows:Country />
          <ows:ElectronicMailAddress />
        </ows:Address>
        <ows:HoursOfService />
        <ows:ContactInstructions />
      </ows:ContactInfo>
      <ows:Role />
    </ows:ServiceContact>
  </ows:ServiceProvider>
  <ows:OperationsMetadata>
    <ows:Operation name="GetCapabilities">
      <ows:DCP>
        <ows:HTTP>
          <ows:Get xlink:href="http://localhost:8080/geonetwork/srv/en/csw" />
          <ows:Post xlink:href="http://localhost:8080/geonetwork/srv/en/csw" />
        </ows:HTTP>
      </ows:DCP>
      <ows:Parameter name="sections">
        <ows:Value>ServiceIdentification</ows:Value>
        <ows:Value>ServiceProvider</ows:Value>
        <ows:Value>OperationsMetadata</ows:Value>
        <ows:Value>Filter_Capabilities</ows:Value>
      </ows:Parameter>
      <ows:Constraint name="PostEncoding">
        <ows:Value>XML</ows:Value>
      </ows:Constraint>
    </ows:Operation>
    <ows:Operation name="DescribeRecord">
      <ows:DCP>
        <ows:HTTP>
          <ows:Get xlink:href="http://localhost:8080/geonetwork/srv/en/csw" />
          <ows:Post xlink:href="http://localhost:8080/geonetwork/srv/en/csw">
            <ows:Constraint name="PostEncoding">
              <ows:Value>XML</ows:Value>
              <ows:Value>SOAP</ows:Value>
            </ows:Constraint>
          </ows:Post>
        </ows:HTTP>
      </ows:DCP>
      <ows:Parameter name="typeName">
        <ows:Value>csw:Record</ows:Value>
        <ows:Value>gmd:MD_Metadata</ows:Value>
      </ows:Parameter>
      <ows:Parameter name="outputFormat">
        <ows:Value>application/xml</ows:Value>
      </ows:Parameter>
      <ows:Parameter name="schemaLanguage">
        <ows:Value>http://www.w3.org/TR/xmlschema-1/</ows:Value>
      </ows:Parameter>
      <ows:Parameter name="typeName">
        <ows:Value>csw:Record</ows:Value>
        <ows:Value>gmd:MD_Metadata</ows:Value>
      </ows:Parameter>
      <ows:Constraint name="PostEncoding">
        <ows:Value>XML</ows:Value>
      </ows:Constraint>
    </ows:Operation>
    <ows:Operation name="GetDomain">
      <ows:DCP>
        <ows:HTTP>
          <ows:Get xlink:href="http://localhost:8080/geonetwork/srv/en/csw" />
          <ows:Post xlink:href="http://localhost:8080/geonetwork/srv/en/csw" />
        </ows:HTTP>
      </ows:DCP>
    </ows:Operation>
    <ows:Operation name="GetRecords">
      <ows:DCP>
        <ows:HTTP>
          <ows:Get xlink:href="http://localhost:8080/geonetwork/srv/en/csw" />
          <ows:Post xlink:href="http://localhost:8080/geonetwork/srv/en/csw">
            <ows:Constraint name="PostEncoding">
              <ows:Value>XML</ows:Value>
              <ows:Value>SOAP</ows:Value>
            </ows:Constraint>
          </ows:Post>
        </ows:HTTP>
      </ows:DCP>
      <!-- FIXME : Gets it from enum or conf -->
      <ows:Parameter name="resultType">
        <ows:Value>hits</ows:Value>
        <ows:Value>results</ows:Value>
        <ows:Value>validate</ows:Value>
      </ows:Parameter>
      <ows:Parameter name="outputFormat">
        <ows:Value>application/xml</ows:Value>
      </ows:Parameter>
      <ows:Parameter name="outputSchema">
        <ows:Value>http://www.opengis.net/cat/csw/2.0.2</ows:Value>
        <ows:Value>http://www.isotc211.org/2005/gmd</ows:Value>
      </ows:Parameter>
      <ows:Parameter name="typeNames">
        <ows:Value>csw:Record</ows:Value>
        <ows:Value>gmd:MD_Metadata</ows:Value>
      </ows:Parameter>
      <ows:Parameter name="CONSTRAINTLANGUAGE">
        <ows:Value>FILTER</ows:Value>
        <ows:Value>CQL_TEXT</ows:Value>
      </ows:Parameter>
      <ows:Constraint name="PostEncoding">
        <ows:Value>XML</ows:Value>
      </ows:Constraint>
      <ows:Constraint name="SupportedISOQueryables">
        <ows:Value>Operation</ows:Value>
        <ows:Value>Format</ows:Value>
        <ows:Value>OrganisationName</ows:Value>
        <ows:Value>Type</ows:Value>
        <ows:Value>ServiceType</ows:Value>
        <ows:Value>DistanceValue</ows:Value>
        <ows:Value>ResourceLanguage</ows:Value>
        <ows:Value>RevisionDate</ows:Value>
        <ows:Value>OperatesOn</ows:Value>
        <ows:Value>GeographicDescriptionCode</ows:Value>
        <ows:Value>AnyText</ows:Value>
        <ows:Value>Modified</ows:Value>
        <ows:Value>PublicationDate</ows:Value>
        <ows:Value>ResourceIdentifier</ows:Value>
        <ows:Value>ParentIdentifier</ows:Value>
        <ows:Value>Identifier</ows:Value>
        <ows:Value>CouplingType</ows:Value>
        <ows:Value>TopicCategory</ows:Value>
        <ows:Value>OperatesOnIdentifier</ows:Value>
        <ows:Value>ServiceTypeVersion</ows:Value>
        <ows:Value>TempExtent_end</ows:Value>
        <ows:Value>Subject</ows:Value>
        <ows:Value>CreationDate</ows:Value>
        <ows:Value>OperatesOnName</ows:Value>
        <ows:Value>Title</ows:Value>
        <ows:Value>DistanceUOM</ows:Value>
        <ows:Value>Denominator</ows:Value>
        <ows:Value>AlternateTitle</ows:Value>
        <ows:Value>Language</ows:Value>
        <ows:Value>TempExtent_begin</ows:Value>
        <ows:Value>HasSecurityConstraints</ows:Value>
        <ows:Value>KeywordType</ows:Value>
        <ows:Value>Abstract</ows:Value>
      </ows:Constraint>
      <ows:Constraint name="AdditionalQueryables">
        <ows:Value>SpecificationDate</ows:Value>
        <ows:Value>ConditionApplyingToAccessAndUse</ows:Value>
        <ows:Value>AccessConstraints</ows:Value>
        <ows:Value>OnlineResourceMimeType</ows:Value>
        <ows:Value>MetadataPointOfContact</ows:Value>
        <ows:Value>SpecificationDateType</ows:Value>
        <ows:Value>Classification</ows:Value>
        <ows:Value>OtherConstraints</ows:Value>
        <ows:Value>OnlineResourceType</ows:Value>
        <ows:Value>Degree</ows:Value>
        <ows:Value>Lineage</ows:Value>
        <ows:Value>SpecificationTitle</ows:Value>
      </ows:Constraint>
    </ows:Operation>
    <ows:Operation name="GetRecordById">
      <ows:DCP>
        <ows:HTTP>
          <ows:Get xlink:href="http://localhost:8080/geonetwork/srv/en/csw" />
          <ows:Post xlink:href="http://localhost:8080/geonetwork/srv/en/csw">
            <ows:Constraint name="PostEncoding">
              <ows:Value>XML</ows:Value>
              <ows:Value>SOAP</ows:Value>
            </ows:Constraint>
          </ows:Post>
        </ows:HTTP>
      </ows:DCP>
      <ows:Parameter name="outputSchema">
        <ows:Value>http://www.opengis.net/cat/csw/2.0.2</ows:Value>
        <ows:Value>http://www.isotc211.org/2005/gmd</ows:Value>
      </ows:Parameter>
      <ows:Parameter name="outputFormat">
        <ows:Value>application/xml</ows:Value>
      </ows:Parameter>
      <ows:Parameter name="resultType">
        <ows:Value>hits</ows:Value>
        <ows:Value>results</ows:Value>
        <ows:Value>validate</ows:Value>
      </ows:Parameter>
      <ows:Parameter name="ElementSetName">
        <ows:Value>brief</ows:Value>
        <ows:Value>summary</ows:Value>
        <ows:Value>full</ows:Value>
      </ows:Parameter>
      <ows:Constraint name="PostEncoding">
        <ows:Value>XML</ows:Value>
      </ows:Constraint>
    </ows:Operation>
    <ows:Operation name="Transaction">
      <ows:DCP>
        <ows:HTTP>
          <ows:Get xlink:href="http://localhost:8080/geonetwork/srv/en/csw" />
          <ows:Post xlink:href="http://localhost:8080/geonetwork/srv/en/csw" />
        </ows:HTTP>
      </ows:DCP>
    </ows:Operation>
    <!--        
        <ows:Operation name="Harvest">
            <ows:DCP>
                <ows:HTTP>
                    <ows:Get  xlink:href="http://$HOST:$PORT$SERVLET/srv/en/csw" />
                    <ows:Post xlink:href="http://$HOST:$PORT$SERVLET/srv/en/csw"  />
                </ows:HTTP>
            </ows:DCP>
        </ows:Operation>
-->
    <ows:Parameter name="service">
      <ows:Value>http://www.opengis.net/cat/csw/2.0.2</ows:Value>
    </ows:Parameter>
    <ows:Parameter name="version">
      <ows:Value>2.0.2</ows:Value>
    </ows:Parameter>
    <ows:Constraint name="IsoProfiles">
      <ows:Value>http://www.isotc211.org/2005/gmd</ows:Value>
    </ows:Constraint>
    <ows:Constraint name="PostEncoding">
      <ows:Value>SOAP</ows:Value>
    </ows:Constraint>
  </ows:OperationsMetadata>
  <ogc:Filter_Capabilities>
    <ogc:Spatial_Capabilities>
      <ogc:GeometryOperands>
        <ogc:GeometryOperand>gml:Envelope</ogc:GeometryOperand>
        <ogc:GeometryOperand>gml:Point</ogc:GeometryOperand>
        <ogc:GeometryOperand>gml:LineString</ogc:GeometryOperand>
        <ogc:GeometryOperand>gml:Polygon</ogc:GeometryOperand>
      </ogc:GeometryOperands>
      <ogc:SpatialOperators>
        <ogc:SpatialOperator name="BBOX" />
        <ogc:SpatialOperator name="Equals" />
        <ogc:SpatialOperator name="Overlaps" />
        <ogc:SpatialOperator name="Disjoint" />
        <ogc:SpatialOperator name="Intersects" />
        <ogc:SpatialOperator name="Touches" />
        <ogc:SpatialOperator name="Crosses" />
        <ogc:SpatialOperator name="Within" />
        <ogc:SpatialOperator name="Contains" />
        <!--
                <ogc:SpatialOperator name="Beyond"/>
                <ogc:SpatialOperator name="DWithin"/>
                 The 'SpatialOperator' element can have a GeometryOperands child -->
      </ogc:SpatialOperators>
    </ogc:Spatial_Capabilities>
    <ogc:Scalar_Capabilities>
      <ogc:LogicalOperators />
      <ogc:ComparisonOperators>
        <ogc:ComparisonOperator>EqualTo</ogc:ComparisonOperator>
        <ogc:ComparisonOperator>Like</ogc:ComparisonOperator>
        <ogc:ComparisonOperator>LessThan</ogc:ComparisonOperator>
        <ogc:ComparisonOperator>GreaterThan</ogc:ComparisonOperator>
        <!-- LessThanOrEqualTo is in OGC Filter Spec, LessThanEqualTo is in OGC CSW schema -->
        <ogc:ComparisonOperator>LessThanEqualTo</ogc:ComparisonOperator>
        <ogc:ComparisonOperator>LessThanOrEqualTo</ogc:ComparisonOperator>
        <!-- GreaterThanOrEqualTo is in OGC Filter Spec, GreaterThanEqualTo is in OGC CSW schema -->
        <ogc:ComparisonOperator>GreaterThanEqualTo</ogc:ComparisonOperator>
        <ogc:ComparisonOperator>GreaterThanOrEqualTo</ogc:ComparisonOperator>
        <ogc:ComparisonOperator>NotEqualTo</ogc:ComparisonOperator>
        <ogc:ComparisonOperator>Between</ogc:ComparisonOperator>
        <ogc:ComparisonOperator>NullCheck</ogc:ComparisonOperator>
        <!-- FIXME : Check NullCheck operation is available -->
      </ogc:ComparisonOperators>
    </ogc:Scalar_Capabilities>
    <ogc:Id_Capabilities>
      <ogc:EID />
      <ogc:FID />
    </ogc:Id_Capabilities>
  </ogc:Filter_Capabilities>
</csw:Capabilities>""" 

    get_records_request_xml = """<?xml version="1.0"?>
<csw:GetRecords xmlns:csw="http://www.opengis.net/cat/csw/2.0.2"
    xmlns:gmd="http://www.isotc211.org/2005/gmd" service="CSW" version="2.0.2" resultType="results">
    <csw:Query typeNames="gmd:MD_Metadata">
        <csw:Constraint version="1.1.0">
            <Filter xmlns="http://www.opengis.net/ogc" xmlns:gml="http://www.opengis.net/gml"/>
        </csw:Constraint>
    </csw:Query>
</csw:GetRecords>"""

    get_records_response_xml = """<?xml version="1.0" encoding="UTF-8"?>
<csw:GetRecordsResponse xmlns:csw="http://www.opengis.net/cat/csw/2.0.2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.opengis.net/cat/csw/2.0.2 http://schemas.opengis.net/csw/2.0.2/CSW-discovery.xsd">
  <csw:SearchStatus timestamp="2010-10-21T14:54:45" />
  <csw:SearchResults numberOfRecordsMatched="3" numberOfRecordsReturned="3" elementSet="summary" nextRecord="0">
    <csw:SummaryRecord xmlns:geonet="http://www.fao.org/geonetwork" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dct="http://purl.org/dc/terms/">
      <dc:identifier>521ca63d-dad9-43fe-aebe-1138ffee530f</dc:identifier>
      <dc:title>Justin's Initial Demo Record.</dc:title>
      <dc:type>dataset</dc:type>
      <dc:subject />
      <dc:format>Please enter the name of the format of the service</dc:format>
      <dct:modified>2010-07-16</dct:modified>
      <dct:abstract>Please enter an abstract, describing the data set more fully</dct:abstract>
    </csw:SummaryRecord>
    <csw:SummaryRecord xmlns:geonet="http://www.fao.org/geonetwork" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dct="http://purl.org/dc/terms/">
      <dc:identifier>8dc2dddd-e483-4c1a-9482-eb05e8e4314d</dc:identifier>
      <dc:title>CKAN Dataset Example 1</dc:title>
      <dc:type>dataset</dc:type>
      <dc:subject>intelligenceMilitary</dc:subject>
      <dc:format>Please enter the name of the format of the service</dc:format>
      <dct:modified>2010-07-16</dct:modified>
      <dct:abstract>This is just an example metadata record, created for the purpose of developing CKAN CSW client capabilities.</dct:abstract>
    </csw:SummaryRecord>
    <csw:SummaryRecord xmlns:geonet="http://www.fao.org/geonetwork" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dct="http://purl.org/dc/terms/">
      <dc:identifier>8d2aaadd-6ad8-41e0-9cd3-ef743ba19887</dc:identifier>
      <dc:title>Testing bug 62 - temporal extents</dc:title>
      <dc:type>dataset</dc:type>
      <dc:subject />
      <dc:format>Please enter the name of the format of the service</dc:format>
      <dct:modified>2010-07-16</dct:modified>
      <dct:abstract>Please enter an abstract, describing the data set more fully</dct:abstract>
    </csw:SummaryRecord>
  </csw:SearchResults>
</csw:GetRecordsResponse>"""

    get_record_by_id_request_xml1 = """<?xml version="1.0"?>
<csw:GetRecordById xmlns:csw="http://www.opengis.net/cat/csw/2.0.2" service="CSW" version="2.0.2"
    outputSchema="csw:IsoRecord">
    <csw:Id>8dc2dddd-e483-4c1a-9482-eb05e8e4314d</csw:Id>
</csw:GetRecordById>"""

    get_record_by_id_response_xml1 = """<?xml version="1.0" encoding="UTF-8"?>
<csw:GetRecordByIdResponse xmlns:csw="http://www.opengis.net/cat/csw/2.0.2">
  <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gsr="http://www.isotc211.org/2005/gsr" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:gss="http://www.isotc211.org/2005/gss" xmlns:gts="http://www.isotc211.org/2005/gts" xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:gmx="http://www.isotc211.org/2005/gmx" xmlns:gco="http://www.isotc211.org/2005/gco" xmlns:geonet="http://www.fao.org/geonetwork">
    <gmd:fileIdentifier xmlns:gml="http://www.opengis.net/gml" xmlns:srv="http://www.isotc211.org/2005/srv">
      <gco:CharacterString>8dc2dddd-e483-4c1a-9482-eb05e8e4314d</gco:CharacterString>
    </gmd:fileIdentifier>
    <gmd:language>
      <gmd:LanguageCode codeList="http://www.loc.gov/standards/iso639-2/php/code_list.php" codeListValue="eng">eng</gmd:LanguageCode>
    </gmd:language>
    <gmd:hierarchyLevel>
      <gmd:MD_ScopeCode codeList="http://www.isotc211.org/2005/resources/codeList.xml#MD_ScopeCode" codeListValue="dataset" />
    </gmd:hierarchyLevel>
    <gmd:dateStamp>
      <gco:DateTime xmlns:gml="http://www.opengis.net/gml" xmlns:srv="http://www.isotc211.org/2005/srv">2010-10-18T18:51:08</gco:DateTime>
    </gmd:dateStamp>
    <gmd:referenceSystemInfo>
      <gmd:MD_ReferenceSystem>
        <gmd:referenceSystemIdentifier>
          <gmd:RS_Identifier>
            <gmd:code>
              <gco:CharacterString>urn:ogc:def:crs:EPSG::4258</gco:CharacterString>
            </gmd:code>
          </gmd:RS_Identifier>
        </gmd:referenceSystemIdentifier>
      </gmd:MD_ReferenceSystem>
    </gmd:referenceSystemInfo>
    <gmd:identificationInfo>
      <gmd:MD_DataIdentification>
        <gmd:citation>
          <gmd:CI_Citation>
            <gmd:title>
              <gco:CharacterString>CKAN Dataset Example 1</gco:CharacterString>
            </gmd:title>
            <gmd:date>
              <gmd:CI_Date>
                <gmd:date>
                  <gco:Date>2010-07-16</gco:Date>
                </gmd:date>
                <gmd:dateType>
                  <gmd:CI_DateTypeCode codeList="http://www.isotc211.org/2005/resources/codeList.xml#CI_DateTypeCode" codeListValue="revision" />
                </gmd:dateType>
              </gmd:CI_Date>
            </gmd:date>
            <gmd:identifier>
              <gmd:RS_Identifier>
                <gmd:code>
                  <gco:CharacterString>Please enter the unique identifier of the dataset</gco:CharacterString>
                </gmd:code>
                <gmd:codeSpace>
                  <gco:CharacterString>Please enter the code space of the unique identifier of the dataset</gco:CharacterString>
                </gmd:codeSpace>
              </gmd:RS_Identifier>
            </gmd:identifier>
          </gmd:CI_Citation>
        </gmd:citation>
        <gmd:abstract>
          <gco:CharacterString>This is just an example metadata record, created for the purpose of developing CKAN CSW client capabilities.</gco:CharacterString>
        </gmd:abstract>
        <gmd:pointOfContact>
          <gmd:CI_ResponsibleParty>
            <gmd:organisationName>
              <gco:CharacterString>Please enter an organisation name for responsible organisation one</gco:CharacterString>
            </gmd:organisationName>
            <gmd:positionName>
              <gco:CharacterString>Please enter a position name for responsible organisation one</gco:CharacterString>
            </gmd:positionName>
            <gmd:contactInfo>
              <gmd:CI_Contact>
                <gmd:address>
                  <gmd:CI_Address>
                    <gmd:electronicMailAddress>
                      <gco:CharacterString>john.bywater@appropriatesoftware.net</gco:CharacterString>
                    </gmd:electronicMailAddress>
                  </gmd:CI_Address>
                </gmd:address>
              </gmd:CI_Contact>
            </gmd:contactInfo>
            <gmd:role>
              <gmd:CI_RoleCode codeList="http://www.isotc211.org/2005/resources/codeList.xml#CI_RoleCode" codeListValue="distributor" />
            </gmd:role>
          </gmd:CI_ResponsibleParty>
        </gmd:pointOfContact>
        <gmd:pointOfContact>
          <gmd:CI_ResponsibleParty>
            <gmd:organisationName>
              <gco:CharacterString>Please enter an organisation name for responsible organisation two</gco:CharacterString>
            </gmd:organisationName>
            <gmd:contactInfo>
              <gmd:CI_Contact>
                <gmd:address>
                  <gmd:CI_Address>
                    <gmd:electronicMailAddress>
                      <gco:CharacterString>john.bywater@appropriatesoftware.net</gco:CharacterString>
                    </gmd:electronicMailAddress>
                  </gmd:CI_Address>
                </gmd:address>
              </gmd:CI_Contact>
            </gmd:contactInfo>
            <gmd:role>
              <gmd:CI_RoleCode codeList="http://www.isotc211.org/2005/resources/codeList.xml#CI_RoleCode" codeListValue="pointOfContact" />
            </gmd:role>
          </gmd:CI_ResponsibleParty>
        </gmd:pointOfContact>
        <gmd:resourceConstraints>
          <gmd:MD_LegalConstraints>
            <gmd:accessConstraints>
              <gmd:MD_RestrictionCode codeList="http://www.isotc211.org/2005/resources/codeList.xml#MD_RestrictionCode" codeListValue="otherRestrictions" />
            </gmd:accessConstraints>
          </gmd:MD_LegalConstraints>
        </gmd:resourceConstraints>
        <gmd:resourceConstraints>
          <gmd:MD_Constraints>
            <gmd:useLimitation>
              <gco:CharacterString>Use limitation</gco:CharacterString>
            </gmd:useLimitation>
          </gmd:MD_Constraints>
        </gmd:resourceConstraints>
        <gmd:spatialResolution>
          <gmd:MD_Resolution>
            <gmd:distance>
              <gco:Distance uom="m">1</gco:Distance>
            </gmd:distance>
          </gmd:MD_Resolution>
        </gmd:spatialResolution>
        <gmd:spatialResolution>
          <gmd:MD_Resolution>
            <gmd:equivalentScale>
              <gmd:MD_RepresentativeFraction>
                <gmd:denominator>
                  <gco:Integer>5000</gco:Integer>
                </gmd:denominator>
              </gmd:MD_RepresentativeFraction>
            </gmd:equivalentScale>
          </gmd:MD_Resolution>
        </gmd:spatialResolution>
        <gmd:language>
          <gmd:LanguageCode codeList="http://www.isotc211.org/2005/resources/codeList.xml#LanguageCode" codeListValue="eng" />
        </gmd:language>
        <gmd:topicCategory>
          <gmd:MD_TopicCategoryCode>intelligenceMilitary</gmd:MD_TopicCategoryCode>
        </gmd:topicCategory>
        <gmd:extent>
          <gmd:EX_Extent>
            <gmd:geographicElement>
              <gmd:EX_GeographicBoundingBox>
                <gmd:westBoundLongitude>
                  <gco:Decimal>-5.4457177734375</gco:Decimal>
                </gmd:westBoundLongitude>
                <gmd:southBoundLatitude>
                  <gco:Decimal>50.115576171875</gco:Decimal>
                </gmd:southBoundLatitude>
                <gmd:eastBoundLongitude>
                  <gco:Decimal>-5.0721826171875</gco:Decimal>
                </gmd:eastBoundLongitude>
                <gmd:northBoundLatitude>
                  <gco:Decimal>50.428686523437</gco:Decimal>
                </gmd:northBoundLatitude>
              </gmd:EX_GeographicBoundingBox>
            </gmd:geographicElement>
          </gmd:EX_Extent>
        </gmd:extent>
      </gmd:MD_DataIdentification>
    </gmd:identificationInfo>
    <gmd:distributionInfo>
      <gmd:MD_Distribution>
        <gmd:distributionFormat>
          <gmd:MD_Format>
            <gmd:name>
              <gco:CharacterString>Please enter the name of the format of the service</gco:CharacterString>
            </gmd:name>
            <gmd:version>
              <gco:CharacterString>Please enter the version of the format of the service</gco:CharacterString>
            </gmd:version>
          </gmd:MD_Format>
        </gmd:distributionFormat>
        <gmd:transferOptions>
          <gmd:MD_DigitalTransferOptions>
            <gmd:onLine>
              <gmd:CI_OnlineResource>
                <gmd:linkage>
                  <gmd:URL>http://appropriatesoftware.net/</gmd:URL>
                </gmd:linkage>
              </gmd:CI_OnlineResource>
            </gmd:onLine>
            <gmd:onLine>
              <gmd:CI_OnlineResource>
                <gmd:linkage>
                  <gmd:URL>http://appropriatesoftware.net/</gmd:URL>
                </gmd:linkage>
              </gmd:CI_OnlineResource>
            </gmd:onLine>
          </gmd:MD_DigitalTransferOptions>
        </gmd:transferOptions>
      </gmd:MD_Distribution>
    </gmd:distributionInfo>
    <gmd:dataQualityInfo>
      <gmd:DQ_DataQuality>
        <gmd:lineage>
          <gmd:LI_Lineage>
            <gmd:statement>
              <gco:CharacterString>Please enter a statement describing the events or sources used in the construction of this dataset</gco:CharacterString>
            </gmd:statement>
          </gmd:LI_Lineage>
        </gmd:lineage>
      </gmd:DQ_DataQuality>
    </gmd:dataQualityInfo>
  </gmd:MD_Metadata>
</csw:GetRecordByIdResponse>"""

    get_record_by_id_request_xml2 = """<?xml version="1.0"?>
<csw:GetRecordById xmlns:csw="http://www.opengis.net/cat/csw/2.0.2" service="CSW" version="2.0.2"
    outputSchema="csw:IsoRecord">
    <csw:Id>521ca63d-dad9-43fe-aebe-1138ffee530f</csw:Id>
</csw:GetRecordById>"""

    get_record_by_id_response_xml2 = """<?xml version="1.0" encoding="UTF-8"?>
<csw:GetRecordByIdResponse xmlns:csw="http://www.opengis.net/cat/csw/2.0.2">
  <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gts="http://www.isotc211.org/2005/gts" xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:gmx="http://www.isotc211.org/2005/gmx" xmlns:gsr="http://www.isotc211.org/2005/gsr" xmlns:gss="http://www.isotc211.org/2005/gss" xmlns:gco="http://www.isotc211.org/2005/gco" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:geonet="http://www.fao.org/geonetwork">
    <gmd:fileIdentifier xmlns:gml="http://www.opengis.net/gml" xmlns:srv="http://www.isotc211.org/2005/srv">
      <gco:CharacterString>521ca63d-dad9-43fe-aebe-1138ffee530f</gco:CharacterString>
    </gmd:fileIdentifier>
    <gmd:language>
      <gmd:LanguageCode codeList="http://www.loc.gov/standards/iso639-2/php/code_list.php" codeListValue="eng">eng</gmd:LanguageCode>
    </gmd:language>
    <gmd:hierarchyLevel>
      <gmd:MD_ScopeCode codeList="http://www.isotc211.org/2005/resources/codeList.xml#MD_ScopeCode" codeListValue="dataset" />
    </gmd:hierarchyLevel>
    <gmd:dateStamp>
      <gco:DateTime xmlns:gml="http://www.opengis.net/gml" xmlns:srv="http://www.isotc211.org/2005/srv">2010-10-12T16:02:48</gco:DateTime>
    </gmd:dateStamp>
    <gmd:referenceSystemInfo>
      <gmd:MD_ReferenceSystem>
        <gmd:referenceSystemIdentifier>
          <gmd:RS_Identifier>
            <gmd:code>
              <gco:CharacterString>urn:ogc:def:crs:EPSG::4258</gco:CharacterString>
            </gmd:code>
          </gmd:RS_Identifier>
        </gmd:referenceSystemIdentifier>
      </gmd:MD_ReferenceSystem>
    </gmd:referenceSystemInfo>
    <gmd:identificationInfo>
      <gmd:MD_DataIdentification>
        <gmd:citation>
          <gmd:CI_Citation>
            <gmd:title>
              <gco:CharacterString>Justin's Initial Demo Record.</gco:CharacterString>
            </gmd:title>
            <gmd:date>
              <gmd:CI_Date>
                <gmd:date>
                  <gco:Date>2010-07-16</gco:Date>
                </gmd:date>
                <gmd:dateType>
                  <gmd:CI_DateTypeCode codeList="http://www.isotc211.org/2005/resources/codeList.xml#CI_DateTypeCode" codeListValue="revision" />
                </gmd:dateType>
              </gmd:CI_Date>
            </gmd:date>
            <gmd:identifier>
              <gmd:RS_Identifier>
                <gmd:code>
                  <gco:CharacterString>Please enter the unique identifier of the dataset</gco:CharacterString>
                </gmd:code>
                <gmd:codeSpace>
                  <gco:CharacterString>Please enter the code space of the unique identifier of the dataset</gco:CharacterString>
                </gmd:codeSpace>
              </gmd:RS_Identifier>
            </gmd:identifier>
          </gmd:CI_Citation>
        </gmd:citation>
        <gmd:abstract>
          <gco:CharacterString>Please enter an abstract, describing the data set more fully</gco:CharacterString>
        </gmd:abstract>
        <gmd:pointOfContact>
          <gmd:CI_ResponsibleParty>
            <gmd:organisationName>
              <gco:CharacterString>Please enter an organisation name for responsible organisation one</gco:CharacterString>
            </gmd:organisationName>
            <gmd:positionName>
              <gco:CharacterString>Please enter a position name for responsible organisation one</gco:CharacterString>
            </gmd:positionName>
            <gmd:contactInfo>
              <gmd:CI_Contact>
                <gmd:address>
                  <gmd:CI_Address>
                    <gmd:electronicMailAddress>
                      <gco:CharacterString>Please enter an email address for responsible organisation one</gco:CharacterString>
                    </gmd:electronicMailAddress>
                  </gmd:CI_Address>
                </gmd:address>
              </gmd:CI_Contact>
            </gmd:contactInfo>
            <gmd:role>
              <gmd:CI_RoleCode codeList="http://www.isotc211.org/2005/resources/codeList.xml#CI_RoleCode" codeListValue="distributor" />
            </gmd:role>
          </gmd:CI_ResponsibleParty>
        </gmd:pointOfContact>
        <gmd:pointOfContact>
          <gmd:CI_ResponsibleParty>
            <gmd:organisationName>
              <gco:CharacterString>Please enter an organisation name for responsible organisation two</gco:CharacterString>
            </gmd:organisationName>
            <gmd:contactInfo>
              <gmd:CI_Contact>
                <gmd:address>
                  <gmd:CI_Address>
                    <gmd:electronicMailAddress>
                      <gco:CharacterString>Please enter an email address for responsible organisation two</gco:CharacterString>
                    </gmd:electronicMailAddress>
                  </gmd:CI_Address>
                </gmd:address>
              </gmd:CI_Contact>
            </gmd:contactInfo>
            <gmd:role>
              <gmd:CI_RoleCode codeList="http://www.isotc211.org/2005/resources/codeList.xml#CI_RoleCode" codeListValue="pointOfContact" />
            </gmd:role>
          </gmd:CI_ResponsibleParty>
        </gmd:pointOfContact>
        <gmd:resourceConstraints>
          <gmd:MD_LegalConstraints>
            <gmd:accessConstraints>
              <gmd:MD_RestrictionCode codeList="http://www.isotc211.org/2005/resources/codeList.xml#MD_RestrictionCode" codeListValue="otherRestrictions" />
            </gmd:accessConstraints>
          </gmd:MD_LegalConstraints>
        </gmd:resourceConstraints>
        <gmd:resourceConstraints>
          <gmd:MD_Constraints>
            <gmd:useLimitation>
              <gco:CharacterString>Use limitation</gco:CharacterString>
            </gmd:useLimitation>
          </gmd:MD_Constraints>
        </gmd:resourceConstraints>
        <gmd:spatialResolution>
          <gmd:MD_Resolution>
            <gmd:distance>
              <gco:Distance uom="urn:ogc:def:uom:EPSG::9001">Please enter the spatial resolution in metres</gco:Distance>
            </gmd:distance>
          </gmd:MD_Resolution>
        </gmd:spatialResolution>
        <gmd:spatialResolution>
          <gmd:MD_Resolution>
            <gmd:equivalentScale>
              <gmd:MD_RepresentativeFraction>
                <gmd:denominator>
                  <gco:Integer>Please enter the denominator of the equivalent scale</gco:Integer>
                </gmd:denominator>
              </gmd:MD_RepresentativeFraction>
            </gmd:equivalentScale>
          </gmd:MD_Resolution>
        </gmd:spatialResolution>
        <gmd:language>
          <gmd:LanguageCode codeList="http://www.isotc211.org/2005/resources/codeList.xml#LanguageCode" codeListValue="eng" />
        </gmd:language>
        <gmd:topicCategory>
          <gmd:MD_TopicCategoryCode />
        </gmd:topicCategory>
        <gmd:extent>
          <gmd:EX_Extent>
            <gmd:geographicElement>
              <gmd:EX_GeographicBoundingBox>
                <gmd:westBoundLongitude>
                  <gco:Decimal>-8.17</gco:Decimal>
                </gmd:westBoundLongitude>
                <gmd:southBoundLatitude>
                  <gco:Decimal>49.96</gco:Decimal>
                </gmd:southBoundLatitude>
                <gmd:eastBoundLongitude>
                  <gco:Decimal>1.75</gco:Decimal>
                </gmd:eastBoundLongitude>
                <gmd:northBoundLatitude>
                  <gco:Decimal>60.84</gco:Decimal>
                </gmd:northBoundLatitude>
              </gmd:EX_GeographicBoundingBox>
            </gmd:geographicElement>
          </gmd:EX_Extent>
        </gmd:extent>
      </gmd:MD_DataIdentification>
    </gmd:identificationInfo>
    <gmd:distributionInfo>
      <gmd:MD_Distribution>
        <gmd:distributionFormat>
          <gmd:MD_Format>
            <gmd:name>
              <gco:CharacterString>Please enter the name of the format of the service</gco:CharacterString>
            </gmd:name>
            <gmd:version>
              <gco:CharacterString>Please enter the version of the format of the service</gco:CharacterString>
            </gmd:version>
          </gmd:MD_Format>
        </gmd:distributionFormat>
        <gmd:transferOptions>
          <gmd:MD_DigitalTransferOptions>
            <gmd:onLine>
              <gmd:CI_OnlineResource>
                <gmd:linkage>
                  <gmd:URL>Please enter the url for further information about the dataset</gmd:URL>
                </gmd:linkage>
              </gmd:CI_OnlineResource>
            </gmd:onLine>
            <gmd:onLine>
              <gmd:CI_OnlineResource>
                <gmd:linkage>
                  <gmd:URL>Please enter the url for the dataset</gmd:URL>
                </gmd:linkage>
              </gmd:CI_OnlineResource>
            </gmd:onLine>
          </gmd:MD_DigitalTransferOptions>
        </gmd:transferOptions>
      </gmd:MD_Distribution>
    </gmd:distributionInfo>
    <gmd:dataQualityInfo>
      <gmd:DQ_DataQuality>
        <gmd:lineage>
          <gmd:LI_Lineage>
            <gmd:statement>
              <gco:CharacterString>Please enter a statement describing the events or sources used in the construction of this dataset</gco:CharacterString>
            </gmd:statement>
          </gmd:LI_Lineage>
        </gmd:lineage>
      </gmd:DQ_DataQuality>
    </gmd:dataQualityInfo>
  </gmd:MD_Metadata>
</csw:GetRecordByIdResponse>"""

    get_record_by_id_request_xml3 = """<?xml version="1.0"?>
<csw:GetRecordById xmlns:csw="http://www.opengis.net/cat/csw/2.0.2" service="CSW" version="2.0.2"
    outputSchema="csw:IsoRecord">
    <csw:Id>8d2aaadd-6ad8-41e0-9cd3-ef743ba19887</csw:Id>
</csw:GetRecordById>"""

    get_record_by_id_response_xml3 = """<?xml version="1.0" encoding="UTF-8"?>
<csw:GetRecordByIdResponse xmlns:csw="http://www.opengis.net/cat/csw/2.0.2">
  <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gts="http://www.isotc211.org/2005/gts" xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:gmx="http://www.isotc211.org/2005/gmx" xmlns:gsr="http://www.isotc211.org/2005/gsr" xmlns:gss="http://www.isotc211.org/2005/gss" xmlns:gco="http://www.isotc211.org/2005/gco" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:geonet="http://www.fao.org/geonetwork">
    <gmd:fileIdentifier xmlns:gml="http://www.opengis.net/gml" xmlns:srv="http://www.isotc211.org/2005/srv">
      <gco:CharacterString>8d2aaadd-6ad8-41e0-9cd3-ef743ba19887</gco:CharacterString>
    </gmd:fileIdentifier>
    <gmd:language>
      <gmd:LanguageCode codeList="http://www.loc.gov/standards/iso639-2/php/code_list.php" codeListValue="eng">eng</gmd:LanguageCode>
    </gmd:language>
    <gmd:hierarchyLevel>
      <gmd:MD_ScopeCode codeList="http://www.isotc211.org/2005/resources/codeList.xml#MD_ScopeCode" codeListValue="dataset" />
    </gmd:hierarchyLevel>
    <gmd:dateStamp>
      <gco:DateTime xmlns:gml="http://www.opengis.net/gml" xmlns:srv="http://www.isotc211.org/2005/srv">2010-10-21T11:44:10</gco:DateTime>
    </gmd:dateStamp>
    <gmd:referenceSystemInfo>
      <gmd:MD_ReferenceSystem>
        <gmd:referenceSystemIdentifier>
          <gmd:RS_Identifier>
            <gmd:code>
              <gco:CharacterString>urn:ogc:def:crs:EPSG::4258</gco:CharacterString>
            </gmd:code>
          </gmd:RS_Identifier>
        </gmd:referenceSystemIdentifier>
      </gmd:MD_ReferenceSystem>
    </gmd:referenceSystemInfo>
    <gmd:identificationInfo>
      <gmd:MD_DataIdentification>
        <gmd:citation>
          <gmd:CI_Citation>
            <gmd:title>
              <gco:CharacterString>Testing bug 62 - temporal extents</gco:CharacterString>
            </gmd:title>
            <gmd:date>
              <gmd:CI_Date>
                <gmd:date>
                  <gco:Date>2010-07-16</gco:Date>
                </gmd:date>
                <gmd:dateType>
                  <gmd:CI_DateTypeCode codeList="http://www.isotc211.org/2005/resources/codeList.xml#CI_DateTypeCode" codeListValue="revision" />
                </gmd:dateType>
              </gmd:CI_Date>
            </gmd:date>
            <gmd:identifier>
              <gmd:RS_Identifier>
                <gmd:code>
                  <gco:CharacterString>Please enter the unique identifier of the dataset</gco:CharacterString>
                </gmd:code>
                <gmd:codeSpace>
                  <gco:CharacterString>Please enter the code space of the unique identifier of the dataset</gco:CharacterString>
                </gmd:codeSpace>
              </gmd:RS_Identifier>
            </gmd:identifier>
          </gmd:CI_Citation>
        </gmd:citation>
        <gmd:abstract>
          <gco:CharacterString>Please enter an abstract, describing the data set more fully</gco:CharacterString>
        </gmd:abstract>
        <gmd:pointOfContact>
          <gmd:CI_ResponsibleParty>
            <gmd:organisationName>
              <gco:CharacterString>Please enter an organisation name for responsible organisation one</gco:CharacterString>
            </gmd:organisationName>
            <gmd:positionName>
              <gco:CharacterString>Please enter a position name for responsible organisation one</gco:CharacterString>
            </gmd:positionName>
            <gmd:contactInfo>
              <gmd:CI_Contact>
                <gmd:address>
                  <gmd:CI_Address>
                    <gmd:electronicMailAddress>
                      <gco:CharacterString>Please enter an email address for responsible organisation one</gco:CharacterString>
                    </gmd:electronicMailAddress>
                  </gmd:CI_Address>
                </gmd:address>
              </gmd:CI_Contact>
            </gmd:contactInfo>
            <gmd:role>
              <gmd:CI_RoleCode codeList="http://www.isotc211.org/2005/resources/codeList.xml#CI_RoleCode" codeListValue="distributor" />
            </gmd:role>
          </gmd:CI_ResponsibleParty>
        </gmd:pointOfContact>
        <gmd:pointOfContact>
          <gmd:CI_ResponsibleParty>
            <gmd:organisationName>
              <gco:CharacterString>Please enter an organisation name for responsible organisation two</gco:CharacterString>
            </gmd:organisationName>
            <gmd:contactInfo>
              <gmd:CI_Contact>
                <gmd:address>
                  <gmd:CI_Address>
                    <gmd:electronicMailAddress>
                      <gco:CharacterString>Please enter an email address for responsible organisation two</gco:CharacterString>
                    </gmd:electronicMailAddress>
                  </gmd:CI_Address>
                </gmd:address>
              </gmd:CI_Contact>
            </gmd:contactInfo>
            <gmd:role>
              <gmd:CI_RoleCode codeList="http://www.isotc211.org/2005/resources/codeList.xml#CI_RoleCode" codeListValue="pointOfContact" />
            </gmd:role>
          </gmd:CI_ResponsibleParty>
        </gmd:pointOfContact>
        <gmd:resourceConstraints>
          <gmd:MD_LegalConstraints>
            <gmd:accessConstraints>
              <gmd:MD_RestrictionCode codeList="http://www.isotc211.org/2005/resources/codeList.xml#MD_RestrictionCode" codeListValue="otherRestrictions" />
            </gmd:accessConstraints>
          </gmd:MD_LegalConstraints>
        </gmd:resourceConstraints>
        <gmd:resourceConstraints>
          <gmd:MD_Constraints>
            <gmd:useLimitation>
              <gco:CharacterString>Use limitation</gco:CharacterString>
            </gmd:useLimitation>
          </gmd:MD_Constraints>
        </gmd:resourceConstraints>
        <gmd:spatialResolution>
          <gmd:MD_Resolution>
            <gmd:distance>
              <gco:Distance uom="urn:ogc:def:uom:EPSG::9001">Please enter the spatial resolution in metres</gco:Distance>
            </gmd:distance>
          </gmd:MD_Resolution>
        </gmd:spatialResolution>
        <gmd:spatialResolution>
          <gmd:MD_Resolution>
            <gmd:equivalentScale>
              <gmd:MD_RepresentativeFraction>
                <gmd:denominator>
                  <gco:Integer>Please enter the denominator of the equivalent scale</gco:Integer>
                </gmd:denominator>
              </gmd:MD_RepresentativeFraction>
            </gmd:equivalentScale>
          </gmd:MD_Resolution>
        </gmd:spatialResolution>
        <gmd:language>
          <gmd:LanguageCode codeList="http://www.isotc211.org/2005/resources/codeList.xml#LanguageCode" codeListValue="eng" />
        </gmd:language>
        <gmd:topicCategory>
          <gmd:MD_TopicCategoryCode />
        </gmd:topicCategory>
        <gmd:extent>
          <gmd:EX_Extent>
            <gmd:geographicElement>
              <gmd:EX_GeographicBoundingBox>
                <gmd:westBoundLongitude>
                  <gco:Decimal>-8.17</gco:Decimal>
                </gmd:westBoundLongitude>
                <gmd:southBoundLatitude>
                  <gco:Decimal>49.96</gco:Decimal>
                </gmd:southBoundLatitude>
                <gmd:eastBoundLongitude>
                  <gco:Decimal>1.75</gco:Decimal>
                </gmd:eastBoundLongitude>
                <gmd:northBoundLatitude>
                  <gco:Decimal>60.84</gco:Decimal>
                </gmd:northBoundLatitude>
              </gmd:EX_GeographicBoundingBox>
            </gmd:geographicElement>
          </gmd:EX_Extent>
        </gmd:extent>
      </gmd:MD_DataIdentification>
    </gmd:identificationInfo>
    <gmd:distributionInfo>
      <gmd:MD_Distribution>
        <gmd:distributionFormat>
          <gmd:MD_Format>
            <gmd:name>
              <gco:CharacterString>Please enter the name of the format of the service</gco:CharacterString>
            </gmd:name>
            <gmd:version>
              <gco:CharacterString>Please enter the version of the format of the service</gco:CharacterString>
            </gmd:version>
          </gmd:MD_Format>
        </gmd:distributionFormat>
        <gmd:transferOptions>
          <gmd:MD_DigitalTransferOptions>
            <gmd:onLine>
              <gmd:CI_OnlineResource>
                <gmd:linkage>
                  <gmd:URL>Please enter the url for further information about the dataset</gmd:URL>
                </gmd:linkage>
              </gmd:CI_OnlineResource>
            </gmd:onLine>
            <gmd:onLine>
              <gmd:CI_OnlineResource>
                <gmd:linkage>
                  <gmd:URL>Please enter the url for the dataset</gmd:URL>
                </gmd:linkage>
              </gmd:CI_OnlineResource>
            </gmd:onLine>
          </gmd:MD_DigitalTransferOptions>
        </gmd:transferOptions>
      </gmd:MD_Distribution>
    </gmd:distributionInfo>
    <gmd:dataQualityInfo>
      <gmd:DQ_DataQuality>
        <gmd:lineage>
          <gmd:LI_Lineage>
            <gmd:statement>
              <gco:CharacterString>Please enter a statement describing the events or sources used in the construction of this dataset</gco:CharacterString>
            </gmd:statement>
          </gmd:LI_Lineage>
        </gmd:lineage>
      </gmd:DQ_DataQuality>
    </gmd:dataQualityInfo>
  </gmd:MD_Metadata>
</csw:GetRecordByIdResponse>"""

    map = {
        get_capabilities_request_xml: get_capabilities_response_xml,
        get_records_request_xml: get_records_response_xml,
        get_record_by_id_request_xml1: get_record_by_id_response_xml1,
        get_record_by_id_request_xml2: get_record_by_id_response_xml2,
        get_record_by_id_request_xml3: get_record_by_id_response_xml3,
    }

    def check_capabilities(self): pass

    def login(self): pass

    def logout(self): pass

    def send(self, csw_request):
        csw_request_xml = self.get_xml_from_csw_request(csw_request)
        if csw_request_xml in self.map:
            csw_response_xml = self.map[csw_request_xml]
        else:
            msg = "Mock send() method can't handle request: %s" % csw_request_xml
            raise Exception, msg
        return csw_response_xml


