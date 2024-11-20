from lxml import etree
from sickle import Sickle
from sickle.models import Record

from dlibra import get_set, get_content_url, get_presentation_data_url


def get_test_record() -> Record:
    """
    Returns a mocked test Record
    """
    xml ="""
    <?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="https://mbc.cyfrowemazowsze.pl/style/common/xsl/oai-style.xsl"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/" 
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/
         http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd">
    <ListRecords>
      <record>
	<header>
		<identifier>oai:mbc.cyfrowemazowsze.pl:59154</identifier>
	    <datestamp>2024-02-27T08:55:31Z</datestamp>
		  <setSpec>MDL:CD</setSpec> 	      <setSpec>MDL:FD:Articles</setSpec> 	      <setSpec>MDL:RM:Varsaviana</setSpec> 	      <setSpec>MDL</setSpec> 	      <setSpec>MDL:FD</setSpec> 	      <setSpec>MDL:RM</setSpec> 	      <setSpec>MDL:FD:Iconography</setSpec> 	      <setSpec>MDL:CD:Warwilustrpras</setSpec> 	    </header>
		<metadata>
	<oai_dc:dc xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/oai_dc/ http://www.openarchives.org/OAI/2.0/oai_dc.xsd">
<dc:title xml:lang="pl"><![CDATA[[Cech szewców] : Puhar czeladzi : Ryngraf czeladniczy]]></dc:title>
<dc:date><![CDATA[[1892]]]></dc:date>
<dc:type xml:lang="pl"><![CDATA[grafika]]></dc:type>
<dc:format xml:lang="pl"><![CDATA[text/xml]]></dc:format>
<dc:identifier><![CDATA[http://aleph.koszykowa.pl/F?func=direct&local_base=BPW01&doc_number=000156913 sygn. P.10113]]></dc:identifier>
<dc:identifier><![CDATA[https://mbc.cyfrowemazowsze.pl/dlibra/publication/edition/59154/content]]></dc:identifier>
<dc:identifier><![CDATA[oai:mbc.cyfrowemazowsze.pl:59154]]></dc:identifier>
<dc:source xml:lang="pl"><![CDATA[Biblioteka Publiczna m.st. Warszawy - Biblioteka Główna Województwa Mazowieckiego]]></dc:source>
<dc:language><![CDATA[pol]]></dc:language>
<dc:relation><![CDATA[Tygodnik Ilustrowany. 1892, Seria 5, T. 5 nr 128, s. 372]]></dc:relation>
<dc:relation><![CDATA[oai:mbc.cyfrowemazowsze.pl:publication:64692]]></dc:relation>
<dc:rights xml:lang="pl"><![CDATA[http://domenapubliczna.org/co-to-jest-domena-publiczna/ Domena publiczna]]></dc:rights>
<dc:rights xml:lang="pl"><![CDATA[Dla wszystkich bez ograniczeń]]></dc:rights>
</oai_dc:dc>

</metadata>
	  </record></ListRecords></OAI-PMH>
    """.strip()

    parsed = etree.fromstring(xml.encode('utf-8'))
    return Record(parsed)

def test_get_presentation_data_url():
    record = get_test_record()
    assert get_presentation_data_url(record) == 'https://mbc.cyfrowemazowsze.pl/Content/59154'


def test_get_content_url():
    record = get_test_record()

    assert record.header.identifier == 'oai:mbc.cyfrowemazowsze.pl:59154'
    assert record.get_metadata().get('date') == ['[1892]']
    assert record.get_metadata().get('language') == ['pol']
    assert get_presentation_data_url(record) == 'https://mbc.cyfrowemazowsze.pl/Content/59154'
    assert get_content_url(record) == 'https://mbc.cyfrowemazowsze.pl/Content/59154/00064692_0000.jpg'

    # this record does not have the XML metadata - it just redirect to an image
    # https://mbc.cyfrowemazowsze.pl/Content/54192/Galeria/00059118-0001.jpg
    record.header.identifier = 'oai:mbc.cyfrowemazowsze.pl:54192'
    assert get_presentation_data_url(record) == 'https://mbc.cyfrowemazowsze.pl/Content/54192'
    assert get_content_url(record) == 'https://mbc.cyfrowemazowsze.pl/Content/54192/Galeria/00059118-0001.jpg'


def test_get_set():
    """
    An integration test
    """
    DLIBRA_SERVER = 'https://mbc.cyfrowemazowsze.pl/'
    # DLIBRA_SERVER = 'https://www.wbc.poznan.pl/'
    OAI_ENDPOINT = f'{DLIBRA_SERVER}dlibra/oai-pmh-repository.xml'
    OAI_SET_NAME = 'MDL:CD:Warwilustrpras'

    harvester = Sickle(OAI_ENDPOINT)
    # skip "certificate verify failed: unable to get local issuer certificate"
    harvester.request_args = {
        'verify': False
    }

    # https://mbc.cyfrowemazowsze.pl//dlibra/oai-pmh-repository.xml?metadataPrefix=oai_dc&set=MDL%3ACD%3AWarwilustrpras&verb=ListRecords
    record = get_set(harvester, OAI_SET_NAME).__next__()

    # print(record.get_metadata())

    assert isinstance(record, Record)
    assert str(record.header.identifier).startswith('oai:mbc.cyfrowemazowsze.pl:')
    assert record.get_metadata().get('language') == ['pol']
