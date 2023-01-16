"""
List MBC sets
"""
import logging
import tempfile
from dataclasses import dataclass

import pywikibot
import requests

from typing import Iterator, List, Tuple, Optional

from lxml.etree import ElementBase
from sickle import Sickle, models, OAIResponse

# TODO: take these from env variables
DLIBRA_SERVER = 'http://mbc.cyfrowemazowsze.pl/'
# DLIBRA_SERVER = 'https://www.wbc.poznan.pl/'
OAI_ENDPOINT = f'{DLIBRA_SERVER}dlibra/oai-pmh-repository.xml'
UPLOAD_COMMENT = 'Importing MBC digital content'

# https://www.wbc.poznan.pl/dlibra/oai-pmh-repository.xml?verb=ListRecords&metadataPrefix=oai_dc&set=rootCollection:wbc:ContemporaryRegionalMagazines
OAI_SET_NAME = 'MDL:CD:Warwilustrpras'


START_FROM_ITEM = 5005

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


def get_content_url(record: models.Record) -> Optional[str]:
    """
    Gets the full content URL for a given record
    """
    logger = logging.getLogger('get_content_url')

    # ('identifier', ['http://mbc.cyfrowemazowsze.pl/Content/59990', ...
    content_xml_url = record.metadata['identifier'][0]
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
    resp = OAIResponse(http_response=requests.get(content_xml_url), params=dict(verb='GetContent'))

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
    url = f'{content_xml_url}/{image_node.text}'
    logger.debug('Content URL: <%s>', url)

    return url


def get_rdf_metadata(record_id: int) -> Iterator[Tuple[str, str]]:
    """
    Iterates over RDF metadata of the provided record
    """
    # @see http://mbc.cyfrowemazowsze.pl/dlibra/rdf.xml?type=e&id=77150
    rdf_url = f'{DLIBRA_SERVER}/dlibra/rdf.xml?type=e&id={record_id}'
    logging.info('Fetching RDF from <%s>', rdf_url)

    resp = OAIResponse(http_response=requests.get(rdf_url), params=dict(verb='GetContent'))
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


def upload_to_commons(site: pywikibot.Site, record: RecordMeta) -> bool:
    """
    Upload a given record to Commons
    """
    logger = logging.getLogger(name='upload_to_commons')
    logger.info('Record metadata: %r', record)

    # format a file name
    # https://commons.wikimedia.org/wiki/File:Portret_Leona_Wagenfisza_(73487).jpg
    file_name = f'{record.title} ({record.record_numeric_id}).jpg'

    file_name = file_name \
        .replace(':', '') \
        .replace('[', '') \
        .replace(']', '')

    file_page = pywikibot.FilePage(source=site, title=file_name)

    # e.g. medium = {{technique|black and white photography}}
    medium = get_medium_for_record(record)
    if medium:
        medium = '{{{{technique|{}}}}}'.format(medium)

    categories = [
        'Uploaded with mbc-harvester',
        'Media contributed by the Mazovian Digital Library',
        'Needing category from the Mazovian Digital Library',
        'Media contributed by the Mazovian Digital Library – needing category',
    ] + get_categories_for_record(record)

    categories_wikitext = '\n'.join([
        f"[[Category:{category}]]"
        for category in categories
    ])

    # prepare a file description with all required details
    file_description = """
=={{int:filedesc}}==
{{Artwork
 |artist = %s
 |description = {{pl|%s}}
 |date = %s
 |medium = %s
 |institution = {{Institution:Mazovian Digital Library}}
 |notes = %s
 |accession number = [http://fbc.pionier.net.pl/id/oai:mbc.cyfrowemazowsze.pl:%d oai:mbc.cyfrowemazowsze.pl:%d]
 |source = 
* http://mbc.cyfrowemazowsze.pl/dlibra/docmetadata?id=%d
* %s
}}

=={{int:license-header}}==
{{PD-old-auto}}
{{Mazovian Digital Library partnership}}

%s
    """.strip() % (
        record.creator, record.title, record.date, medium, record.notes,
        record.record_numeric_id, record.record_numeric_id, record.record_numeric_id,
        record.source, categories_wikitext
    )

    logger.info('File page: %r', file_page)
    logger.info('File description: %s', file_description)

    if file_page.exists():
        logger.info('%r exists, skipping an upload', file_page)
        return False

    # now fetch the resource to a local temporary file
    with tempfile.NamedTemporaryFile(prefix='mbc-harvest-') as temp_upload:
        logger.info('Fetching <%s> into %s temporary file', record.content_url, temp_upload.name)

        response = requests.get(record.content_url)

        response_size = int(response.headers['content-length'] or 0) / 1024 / 1024
        logger.info('HTTP %d (%.2f MB)', response.status_code, response_size)

        # write the response to a temporary file
        temp_upload.write(response.content)

        # and upload from the file
        ret = file_page.upload(
            source=temp_upload.name,
            text=file_description,
            comment=UPLOAD_COMMENT,
            report_success=True,
            ignore_warnings=False,
        )

    return ret


def main():
    logger = logging.getLogger('oai-harvester')
    logger.info('Using <%s> OAI endpoint', OAI_ENDPOINT)

    harvester = Sickle(OAI_ENDPOINT)

    # https://www.mediawiki.org/wiki/Manual:Pywikibot/Create_your_own_script
    # https://doc.wikimedia.org/pywikibot/master/api_ref/index.html
    commons = pywikibot.Site()
    commons.login()
    logger.info('pywikibot: %r', commons)

    for idx, record in enumerate(get_set(harvester, OAI_SET_NAME)):
        if idx < START_FROM_ITEM:
            logger.info('Skipping record #%d due to START_FROM_ITEM', idx)
            continue

        logger.info('---')
        logger.info('Record #%d found: %r', idx + 1, record)
        # logger.info('Metadata: %r', record.metadata)

        # oai:mbc.cyfrowemazowsze.pl:59990
        try:
            # oai:mbc.cyfrowemazowsze.pl:59990 -> mbc.cyfrowemazowsze.pl
            source_id = str(record.header.identifier).split(':')[1]
            record_id = int(str(record.header.identifier).split(':')[-1])

            content_url = get_content_url(record)
            if not content_url:
                continue

            record_meta = RecordMeta(
                record_id=record.header.identifier,
                source_id=source_id,
                title=record.metadata['title'][0],
                medium=record.metadata['type'][0],  # e.g. grafika
                date=str(record.metadata['date'][0]).strip('[]'),
                content_url=content_url,
                tags=sorted(list(set(record.metadata['subject']))),
            )

            # fetch additional metadata from RDF endpoint
            # http://mbc.cyfrowemazowsze.pl/dlibra/rdf.xml?type=e&id=77150
            # notes = <dc:description xml:lang="pl">1 grafika : drzewor. ; 11,2x13,8 cm</dc:description>
            # source = <dc:relation xml:lang="pl">Kłosy. 1886, t.43 nr 1105 s. 149</dc:relation>
            for key, value in get_rdf_metadata(record_id=record_id):
                # Biblioteka Publiczna m.st. Warszawy - Biblioteka Główna Województwa Mazowieckiego
                if key == 'description' and 'Biblioteka' not in value:
                    record_meta.notes = value
                elif key == 'relation':
                    record_meta.source = value
                elif key == 'creator':
                    record_meta.creator = value

            # logger.info('Raw record: %s', json.dumps(record.metadata, indent=True))
            upload_to_commons(site=commons, record=record_meta)

        except:
            logger.error('Exception', exc_info=True)
            pass

        # DEBUG
        # if idx > 75:
        #    break


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
