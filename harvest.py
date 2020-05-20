"""
List MBC sets
"""
import json
import logging
from dataclasses import dataclass

import pywikibot
import requests

from typing import Iterator, List, Tuple, Optional

from lxml.etree import ElementBase
from sickle import Sickle, models, OAIResponse

DLIBRA_SERVER = 'http://mbc.cyfrowemazowsze.pl/'
# DLIBRA_SERVER = 'https://www.wbc.poznan.pl/'
OAI_ENDPOINT = f'{DLIBRA_SERVER}dlibra/oai-pmh-repository.xml'
UPLOAD_COMMENT = 'Import MBC content'


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


def get_content_url(record: models.Record) -> str:
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


def upload_to_commons(site: pywikibot.Site, record: RecordMeta) -> bool:
    """
    Upload a given record to Commons
    """
    logger = logging.getLogger(name='upload_to_commons')
    logger.info('Record metadata: %r', record)

    # format a file name
    # https://commons.wikimedia.org/wiki/File:Portret_Leona_Wagenfisza_(73487).jpg
    file_name = f'{record.title} ({record.record_numeric_id}).jpg'

    file_name = file_name\
        .replace(':', '')\
        .replace('[', '')\
        .replace(']', '')

    file_page = pywikibot.FilePage(source=site, title=file_name)

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

[[Category:Media contributed by the Mazovian Digital Library]]
[[Category:Media contributed by the Mazovian Digital Library – needing category‎]]

[[Category:Uploaded with mbc-harvester]]
    """.strip() % \
        (record.creator, record.title, record.date, record.medium, record.notes,
         record.record_numeric_id, record.record_numeric_id, record.record_numeric_id,
         record.source)

    logger.info('File page: %r', file_page)
    logger.info('File description: %s', file_description)

    if file_page.exists():
        logger.info('%r exists, skipping an upload', file_page)
        return False

    return file_page.upload(
        source=record.content_url,
        text=file_description,
        comment=UPLOAD_COMMENT,
        report_success=True,
    )


def main():
    logger = logging.getLogger('oai-harvester')
    logger.info('Using <%s> OAI endpoint',  OAI_ENDPOINT)

    harvester = Sickle(OAI_ENDPOINT)

    # https://www.mediawiki.org/wiki/Manual:Pywikibot/Create_your_own_script
    # https://doc.wikimedia.org/pywikibot/master/api_ref/index.html
    commons = pywikibot.Site()
    commons.login()
    logger.info('pywikibot: %r', commons._siteinfo)

    # https://www.wbc.poznan.pl/dlibra/oai-pmh-repository.xml?verb=ListRecords&metadataPrefix=oai_dc&set=rootCollection:wbc:ContemporaryRegionalMagazines
    set_name = 'MDL:CD:Warwilustrpras'

    for idx, record in enumerate(get_set(harvester, set_name)):
        logger.info('---')
        logger.info('Record #%d found: %r', idx+1, record)
        # logger.info('Metadata: %r', record.metadata)

        # oai:mbc.cyfrowemazowsze.pl:59990
        try:
            # oai:mbc.cyfrowemazowsze.pl:59990 -> mbc.cyfrowemazowsze.pl
            source_id = str(record.header.identifier).split(':')[1]
            record_id = int(str(record.header.identifier).split(':')[-1])

            record_meta = RecordMeta(
                record_id=record.header.identifier,
                source_id=source_id,
                title=record.metadata['title'][0],
                medium=record.metadata['type'][0],  # e.g. grafika
                date=str(record.metadata['date'][0]).strip('[]'),
                content_url=get_content_url(record),
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
        if idx > 2:
            break


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
