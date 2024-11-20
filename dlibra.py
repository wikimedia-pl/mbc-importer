"""
dLibra handling utilities

http://dingo.psnc.pl/
"""
import logging
import urllib3

from dataclasses import dataclass
from typing import Iterator, List, Tuple, Optional

from lxml.etree import ElementBase
from requests import Session
from sickle import Sickle, models, OAIResponse


# prepare the HTTP clint
http_session = Session()
http_session.headers['user-agent'] = 'mbc-harvest (+https://github.com/wikimedia-pl/mbc-importer)'
http_session.verify = False  # prevent "certificate verify failed: unable to get local issuer certificate" error
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)



@dataclass
class RecordMeta:
    """
    Encapsulates metadata of the record needed to upload a file to Wikimedia Commons
    """
    record_id: str  # e.g. oai:mbc.cyfrowemazowsze.pl:59990
    source_id: str
    title: str
    medium: str
    date: str
    content_url: str
    tags: List[str]

    creator: Optional[str] = ''
    notes: Optional[str] = ''
    source: Optional[str] = ''

    @property
    def record_numeric_id(self) -> int:
        """
        oai:mbc.cyfrowemazowsze.pl:59990 -> 59990
        """
        return int(str(self.record_id).split(':')[-1])


def get_set(instance: Sickle, set_name: str) -> Iterator[models.Record]:
    return instance.ListRecords(
        metadataPrefix='oai_dc',
        set=set_name
    )


def get_presentation_data_url(record: models.Record) -> str:
    """
    Returns URL to the XML doc with the record metadata

    curl https://mbc.cyfrowemazowsze.pl/Content/59154/PresentationData.xml
    """
    ident: str = record.header.identifier  # oai:mbc.cyfrowemazowsze.pl:59154
    parts = ident.split(':')

    return f'https://{parts[1]}/Content/{parts[2]}/PresentationData.xml'



def get_content_url(record: models.Record) -> Optional[str]:
    """
    Gets the full content URL for a given record
    """
    logger = logging.getLogger('get_content_url')

    content_xml_url = get_presentation_data_url(record)
    logger.debug('Fetching content URL from <%s> ...', content_xml_url)

    """
    <?xml version="1.0" encoding="UTF-8" standalone="no"?>
    <object-presentation>
    <presentation-elements>
    <presentation-element position="0">
    <full-image><![CDATA[00064995_0000.jpg]]></full-image>
    </presentation-element>
    </presentation-elements>
    </object-presentation>
    """
    resp = OAIResponse(http_response=http_session.get(content_xml_url), params=dict(verb='GetContent'))

    if resp.xml is None:
        content_type = str(resp.http_response.headers.get('Content-Type'))
        logger.debug('Headers: %r', resp.http_response.headers)

        # we got the image as an redirect, e.g. http://mbc.cyfrowemazowsze.pl/Content/54558
        if content_type.startswith('image/'):
            return resp.http_response.url

        logger.warning('No XML found at <%s> ...', content_xml_url)
        return None

    # 00064995_0000.jpg
    image_node: ElementBase = resp.xml.find('.//full-image')

    # this will become
    # http://mbc.cyfrowemazowsze.pl/Content/61991/00066224_0000.jpg

    ident: str = record.header.identifier  # oai:mbc.cyfrowemazowsze.pl:59154
    parts = ident.split(':')

    url = f'https://{parts[1]}/Content/{parts[2]}/{image_node.text}'
    logger.debug('Content URL: <%s>', url)

    return url


def get_rdf_metadata(dlibra_server: str, record_id: int) -> Iterator[Tuple[str, str]]:
    """
    Iterates over RDF metadata of the provided record
    """
    # @see http://mbc.cyfrowemazowsze.pl/dlibra/rdf.xml?type=e&id=77150
    rdf_url = f'{dlibra_server}/dlibra/rdf.xml?type=e&id={record_id}'
    logging.info('Fetching RDF from <%s>', rdf_url)

    resp = OAIResponse(http_response=http_session.get(rdf_url), params=dict(verb='GetContent'))
    root_node: ElementBase = next(resp.xml.iterchildren())
    for node in root_node.iterchildren():
        # {http://purl.org/dc/elements/1.1/}relation Tygodnik Illustrowany. 1890, Seria 5, T.2 nr 49, s. 371
        tag_name = str(node.tag).replace('{http://purl.org/dc/elements/1.1/}', '')

        yield tag_name, node.text


def get_medium_for_record(record: RecordMeta) -> Optional[str]:
    """
    Returns medium for Commons
    """
    if record.medium == 'fotografia':
        return 'black and white photography'

    if record.medium == 'grafika':
        if 'Drzeworyt' in record.tags:
            return 'woodcut'

        if 'Litografia' in record.tags:
            return 'lithography'

        return 'drawing'

    return None


def get_categories_for_record(record: RecordMeta) -> List[str]:
    """
    Returns additional categories for a given record
    """
    categories = []

    # http://mbc.cyfrowemazowsze.pl/dlibra/oai-pmh-repository.xml?verb=GetRecord&metadataPrefix=oai_dc&identifier=oai:mbc.cyfrowemazowsze.pl:73487
    # e.g. 'Portrety - Polska - 19-20 w.' => 'Media contributed by the Mazovian Digital Library (Portrety XIX wiek)‎'
    # e.g. 'Warszawa - służba zdrowia - 19 w.' => 'Media contributed by the Mazovian Digital Library (służba zdrowia)'
    # https://commons.wikimedia.org/wiki/Category:Media_contributed_by_the_Mazovian_Digital_Library_by_topic
    if 'Portrety - Polska - 19-20 w.' in record.tags:
        categories.append('Media contributed by the Mazovian Digital Library (Portrety XIX wiek)‎')

    if 'Warszawa - służba zdrowia - 19 w.' in record.tags:
        categories.append('Media contributed by the Mazovian Digital Library (służba zdrowia)‎')

    return categories

