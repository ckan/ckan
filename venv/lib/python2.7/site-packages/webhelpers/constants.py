# -*- encoding: latin-1 -*-
# Latin-1 encoding needed for countries list.
"""Place names and other constants often used in web forms.
"""

def uk_counties():
    """\
    Return a list of UK county names.
    """
    # Based on http://www.gbet.com/AtoZ_counties/
    # Updated 2007-10-24
    return [x.strip()[2:] for x in """\
    * Avon
    * Bedfordshire
    * Berkshire
    * Borders
    * Buckinghamshire
    * Cambridgeshire
    * Central
    * Cheshire
    * Cleveland
    * Clwyd
    * Cornwall
    * County Antrim
    * County Armagh
    * County Down
    * County Fermanagh
    * County Londonderry
    * County Tyrone
    * Cumbria
    * Derbyshire
    * Devon
    * Dorset
    * Dumfries and Galloway
    * Durham
    * Dyfed
    * East Sussex
    * Essex
    * Fife
    * Gloucestershire
    * Grampian
    * Greater Manchester
    * Gwent
    * Gwynedd County
    * Hampshire
    * Herefordshire
    * Hertfordshire
    * Highlands and Islands
    * Humberside
    * Isle of Wight
    * Kent
    * Lancashire
    * Leicestershire
    * Lincolnshire
    * Lothian
    * Merseyside
    * Mid Glamorgan
    * Norfolk
    * North Yorkshire
    * Northamptonshire
    * Northumberland
    * Nottinghamshire
    * Oxfordshire
    * Powys
    * Rutland
    * Shropshire
    * Somerset
    * South Glamorgan
    * South Yorkshire
    * Staffordshire
    * Strathclyde
    * Suffolk
    * Surrey
    * Tayside
    * Tyne and Wear
    * Warwickshire
    * West Glamorgan
    * West Midlands
    * West Sussex
    * West Yorkshire
    * Wiltshire
    * Worcestershire""".split('\n')]

_country_codes = None
def country_codes():
    """Return a list of all country names as tuples. The tuple value is the
    country's 2-letter ISO code and its name; e.g., 
    ``("GB", "United Kingdom")``. The countries are in name order.
    
    Can be used like this::

        import webhelpers.constants as constants
        from webhelpers.html.tags import select
        select("country", country_codes(),
            prompt="Please choose a country ...")

    See here for more information:
    http://www.iso.org/iso/english_country_names_and_code_elements
    """
    # Updated on 2007-10-24.
    #
    # This might seem a funny implementation but it makes it easier to update
    # next time there is a change

    global _country_codes
    if _country_codes is not None:
        return _country_codes
    else:
        
        text_directly_from_iso_website = u"""
A   	  
AFGHANISTAN 	AF
ÅLAND ISLANDS 	AX
ALBANIA 	AL
ALGERIA 	DZ
AMERICAN SAMOA 	AS
ANDORRA 	AD
ANGOLA 	AO
ANGUILLA 	AI
ANTARCTICA 	AQ
ANTIGUA AND BARBUDA 	AG
ARGENTINA 	AR
ARMENIA 	AM
ARUBA 	AW
AUSTRALIA 	AU
AUSTRIA 	AT
AZERBAIJAN 	AZ
B 	 
BAHAMAS 	BS
BAHRAIN 	BH
BANGLADESH 	BD
BARBADOS 	BB
BELARUS 	BY
BELGIUM 	BE
BELIZE 	BZ
BENIN 	BJ
BERMUDA 	BM
BHUTAN 	BT
BOLIVIA 	BO
BOSNIA AND HERZEGOVINA 	BA
BOTSWANA 	BW
BOUVET ISLAND 	BV
BRAZIL 	BR
BRITISH INDIAN OCEAN TERRITORY 	IO
BRUNEI DARUSSALAM 	BN
BULGARIA 	BG
BURKINA FASO 	BF
BURUNDI 	BI
C 	 
CAMBODIA 	KH
CAMEROON 	CM
CANADA 	CA
CAPE VERDE 	CV
CAYMAN ISLANDS 	KY
CENTRAL AFRICAN REPUBLIC 	CF
CHAD 	TD
CHILE 	CL
CHINA 	CN
CHRISTMAS ISLAND 	CX
COCOS (KEELING) ISLANDS 	CC
COLOMBIA 	CO
COMOROS 	KM
CONGO 	CG
CONGO, THE DEMOCRATIC REPUBLIC OF THE 	CD
COOK ISLANDS 	CK
COSTA RICA 	CR
CÔTE D'IVOIRE 	CI
CROATIA 	HR
CUBA 	CU
CYPRUS 	CY
CZECH REPUBLIC 	CZ
D 	 
DENMARK 	DK
DJIBOUTI 	DJ
DOMINICA 	DM
DOMINICAN REPUBLIC 	DO
E 	 
ECUADOR 	EC
EGYPT 	EG
EL SALVADOR 	SV
EQUATORIAL GUINEA 	GQ
ERITREA 	ER
ESTONIA 	EE
ETHIOPIA 	ET
F 	 
FALKLAND ISLANDS (MALVINAS) 	FK
FAROE ISLANDS 	FO
FIJI 	FJ
FINLAND 	FI
FRANCE 	FR
FRENCH GUIANA 	GF
FRENCH POLYNESIA 	PF
FRENCH SOUTHERN TERRITORIES 	TF
G 	 
GABON 	GA
GAMBIA 	GM
GEORGIA 	GE
GERMANY 	DE
GHANA 	GH
GIBRALTAR 	GI
GREECE 	GR
GREENLAND 	GL
GRENADA 	GD
GUADELOUPE 	GP
GUAM 	GU
GUATEMALA 	GT
GUERNSEY 	GG
GUINEA 	GN
GUINEA-BISSAU 	GW
GUYANA 	GY
H 	 
HAITI 	HT
HEARD ISLAND AND MCDONALD ISLANDS 	HM
HOLY SEE (VATICAN CITY STATE) 	VA
HONDURAS 	HN
HONG KONG 	HK
HUNGARY 	HU
I 	 
ICELAND 	IS
INDIA 	IN
INDONESIA 	ID
IRAN, ISLAMIC REPUBLIC OF 	IR
IRAQ 	IQ
IRELAND 	IE
ISLE OF MAN 	IM
ISRAEL 	IL
ITALY 	IT
J 	 
JAMAICA 	JM
JAPAN 	JP
JERSEY 	JE
JORDAN 	JO
K 	 
KAZAKHSTAN 	KZ
KENYA 	KE
KIRIBATI 	KI
KOREA, DEMOCRATIC PEOPLE'S REPUBLIC OF 	KP
KOREA, REPUBLIC OF 	KR
KUWAIT 	KW
KYRGYZSTAN 	KG
L 	 
LAO PEOPLE'S DEMOCRATIC REPUBLIC 	LA
LATVIA 	LV
LEBANON 	LB
LESOTHO 	LS
LIBERIA 	LR
LIBYAN ARAB JAMAHIRIYA 	LY
LIECHTENSTEIN 	LI
LITHUANIA 	LT
LUXEMBOURG 	LU
M 	 
MACAO 	MO
MACEDONIA, THE FORMER YUGOSLAV REPUBLIC OF 	MK
MADAGASCAR 	MG
MALAWI 	MW
MALAYSIA 	MY
MALDIVES 	MV
MALI 	ML
MALTA 	MT
MARSHALL ISLANDS 	MH
MARTINIQUE 	MQ
MAURITANIA 	MR
MAURITIUS 	MU
MAYOTTE 	YT
MEXICO 	MX
MICRONESIA, FEDERATED STATES OF 	FM
MOLDOVA, REPUBLIC OF 	MD
MONACO 	MC
MONGOLIA 	MN
MONTENEGRO 	ME
MONTSERRAT 	MS
MOROCCO 	MA
MOZAMBIQUE 	MZ
MYANMAR 	MM
N 	 
NAMIBIA 	NA
NAURU 	NR
NEPAL 	NP
NETHERLANDS 	NL
NETHERLANDS ANTILLES 	AN
NEW CALEDONIA 	NC
NEW ZEALAND 	NZ
NICARAGUA 	NI
NIGER 	NE
NIGERIA 	NG
NIUE 	NU
NORFOLK ISLAND 	NF
NORTHERN MARIANA ISLANDS 	MP
NORWAY 	NO
O 	 
OMAN 	OM
P 	 
PAKISTAN 	PK
PALAU 	PW
PALESTINIAN TERRITORY, OCCUPIED 	PS
PANAMA 	PA
PAPUA NEW GUINEA 	PG
PARAGUAY 	PY
PERU 	PE
PHILIPPINES 	PH
PITCAIRN 	PN
POLAND 	PL
PORTUGAL 	PT
PUERTO RICO 	PR
Q 	 
QATAR 	QA
R 	
RÉUNION 	RE
ROMANIA 	RO
RUSSIAN FEDERATION 	RU
RWANDA 	RW
S 	 
SAINT BARTHÉLEMY 	BL
SAINT HELENA 	SH
SAINT KITTS AND NEVIS 	KN
SAINT LUCIA 	LC
SAINT MARTIN 	MF
SAINT PIERRE AND MIQUELON 	PM
SAINT VINCENT AND THE GRENADINES 	VC
SAMOA 	WS
SAN MARINO 	SM
SAO TOME AND PRINCIPE 	ST
SAUDI ARABIA 	SA
SENEGAL 	SN
SERBIA 	RS
SEYCHELLES 	SC
SIERRA LEONE 	SL
SINGAPORE 	SG
SLOVAKIA 	SK
SLOVENIA 	SI
SOLOMON ISLANDS 	SB
SOMALIA 	SO
SOUTH AFRICA 	ZA
SOUTH GEORGIA AND THE SOUTH SANDWICH ISLANDS 	GS
SPAIN 	ES
SRI LANKA 	LK
SUDAN 	SD
SURINAME 	SR
SVALBARD AND JAN MAYEN 	SJ
SWAZILAND 	SZ
SWEDEN 	SE
SWITZERLAND 	CH
SYRIAN ARAB REPUBLIC 	SY
T 	 
TAIWAN, PROVINCE OF CHINA 	TW
TAJIKISTAN 	TJ
TANZANIA, UNITED REPUBLIC OF 	TZ
THAILAND 	TH
TIMOR-LESTE 	TL
TOGO 	TG
TOKELAU 	TK
TONGA 	TO
TRINIDAD AND TOBAGO 	TT
TUNISIA 	TN
TURKEY 	TR
TURKMENISTAN 	TM
TURKS AND CAICOS ISLANDS 	TC
TUVALU 	TV
U 	 
UGANDA 	UG
UKRAINE 	UA
UNITED ARAB EMIRATES 	AE
UNITED KINGDOM 	GB
UNITED STATES 	US
UNITED STATES MINOR OUTLYING ISLANDS 	UM
URUGUAY 	UY
UZBEKISTAN 	UZ
V 	 
VANUATU 	VU
VATICAN CITY STATE 	see HOLY SEE
VENEZUELA 	VE
VIET NAM 	VN
VIRGIN ISLANDS, BRITISH 	VG
VIRGIN ISLANDS, U.S. 	VI
W 	 
WALLIS AND FUTUNA 	WF
WESTERN SAHARA 	EH
Y 	 
YEMEN 	YE
Z 	 
ZAIRE 	see CONGO, THE DEMOCRATIC REPUBLIC OF THE
ZAMBIA 	ZM
ZIMBABWE 	ZW
""".replace('\t','    ').split('\n')
    e = []
    for item in text_directly_from_iso_website:
        if len(item) > 1:
            p=[]
            parts = item.split('  ')
            for part in parts:
                if part.strip():
                    p.append(part.strip())
            if len(p)>2:
                raise Exception("Invalid entry %s" % p)

            p.reverse()
            if len(p) == 1:
                # It is just a letter
                continue
            if len(p[0]) != 2:
                if p[0][:3] != 'see':
                    raise Exception('Unknown entry %s'%(p))
                else:
                    # We just want to ignore it
                    continue
            p = tuple(p)
            e.append(p)
    _country_codes = e
    return _country_codes

def us_states():
    """List of USA states.

    Return a list of ``(abbreviation, name)`` for all US states, sorted by name.
    Includes the District of Columbia.
    """
    # From http://www.usps.com/ncsc/lookups/abbreviations.html
    #Updated 2008-05-01
    return [
        ("AL", "Alabama"),
        ("AK", "Alaska"),
        ("AZ", "Arizona"),
        ("AR", "Arkansas"),
        ("CA", "California"),
        ("CO", "Colorado"),
        ("CT", "Connecticut"),
        ("DE", "Delaware"),
        ("DC", "District of Columbia"),
        ("FL", "Florida"),
        ("GA", "Georgia"),
        ("HI", "Hawaii"),
        ("ID", "Idaho"),
        ("IL", "Illinois"),
        ("IN", "Indiana"),
        ("IA", "Iowa"),
        ("KS", "Kansas"),
        ("KY", "Kentucky"),
        ("LA", "Louisiana"),
        ("ME", "Maine"),
        ("MD", "Maryland"),
        ("MA", "Massachusetts"),
        ("MI", "Michigan"),
        ("MN", "Minnesota"),
        ("MS", "Mississippi"),
        ("MO", "Missouri"),
        ("MT", "Montana"),
        ("NE", "Nebraska"),
        ("NV", "Nevada"),
        ("NH", "New Hampshire"),
        ("NJ", "New Jersey"),
        ("NM", "New Mexico"),
        ("NY", "New York"),
        ("NC", "North Carolina"),
        ("ND", "North Dakota"),
        ("OH", "Ohio"),
        ("OK", "Oklahoma"),
        ("OR", "Oregon"),
        ("PA", "Pennsylvania"),
        ("RI", "Rhode Island"),
        ("SC", "South Carolina"),
        ("SD", "South Dakota"),
        ("TN", "Tennessee"),
        ("TX", "Texas"),
        ("UT", "Utah"),
        ("VT", "Vermont"),
        ("VA", "Virginia"),
        ("WA", "Washington"),
        ("WV", "West Virginia"),
        ("WI", "Wisconsin"),
        ("WY", "Wyoming"),
        ]

def us_territories():
    """USA postal abbreviations for territories, protectorates, and military.
    
    The return value is a list of ``(abbreviation, name)`` tuples. The
    locations are sorted by name.
    """
    # From http://www.usps.com/ncsc/lookups/abbreviations.html
    # Updated 2008-05-01
    return [
        ("AS", "American Samoa"),
        ("AA", "Armed Forces Americas"),
        ("AE", "Armed Forces Europe/Canada/Middle East/Africa"),
        ("AP", "Armed Forces Pacific"),
        ("FM", "Federated States of Micronesia"),
        ("GU", "Guam"),
        ("MH", "Marshall Islands"),
        ("MP", "Northern Mariana Islands"),
        ("PW", "Palau"),
        ("PR", "Puerto Rico"),
        ("VI", "Virgin Islands"),
        ]
    

def canada_provinces():
    """List of Canadian provinces.

    Return a list of ``(abbreviation, name)`` tuples for all Canadian
    provinces and territories, sorted by name.
    """
    # Based on:
    # http://en.wikipedia.org/wiki/Canadian_subnational_postal_abbreviations
    # See also: 
    # http://en.wikipedia.org/wiki/Provinces_and_territories_of_Canada
    # Updated 2008-05-01
    provinces = [
        ("Alberta", "AB"),
        ("British Columbia", "BC"),
        ("Manitoba", "MB"),
        ("New Brunswick", "NB"),
        ("Newfoundland and Labrador", "NL"),
        ("Nova Scotia", "NS"),
        ("Northwest Territories", "NT"),
        ("Nunavut", "NU"),
        ("Ontario", "ON"),
        ("Prince Edward Island", "PE"),
        ("Quebec", "QC"),
        ("Saskatchewan", "SK"),
        ("Yukon", "YT"),
        ]
    provinces.sort()
    return [(x[1], x[0]) for x in provinces]
