"""
List MBC sets
"""
import logging
from dataclasses import dataclass

import pywikibot
import requests

from typing import Iterator, List

from lxml.etree import ElementBase
from sickle import Sickle, models, OAIResponse

DLIBRA_SERVER = 'http://mbc.cyfrowemazowsze.pl/'
# DLIBRA_SERVER = 'https://www.wbc.poznan.pl/'
OAI_ENDPOINT = f'{DLIBRA_SERVER}dlibra/oai-pmh-repository.xml'


@dataclass
class RecordMeta:
    """
    Encapsulates metadata of the record needed to upload a file to Wikimedia Commons
    """
    record_id: str  # e.g. oai:mbc.cyfrowemazowsze.pl:59990
    source_id: str
    title: str
    date: str
    content_url: str
    tags: List[str]

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


def upload_to_commons(record: RecordMeta):
    """
    Upload a given record to Commons
    """
    logger = logging.getLogger(name='upload_to_commons')

    # format a file name
    # https://commons.wikimedia.org/wiki/File:Portret_Leona_Wagenfisza_(73487).jpg
    file_name = f'{record.title} ({record.record_numeric_id}).jpg'

    file_desciption = """
=={{int:filedesc}}==
{{Artwork
 |artist = 
 |description = {{pl|%s}}
 |date = %s
 |medium =
 |institution = {{Institution:Mazovian Digital Library}}
 |notes =
 |accession number = [http://fbc.pionier.net.pl/id/oai:mbc.cyfrowemazowsze.pl:%d oai:mbc.cyfrowemazowsze.pl:%d]
 |source = 
* http://mbc.cyfrowemazowsze.pl/dlibra/docmetadata?id=%d

}}

=={{int:license-header}}==
{{PD-old-auto}}
{{Mazovian Digital Library partnership}}

[[Category:Media contributed by the Mazovian Digital Library (Ilustracja prasowa z XIX w.)]]

[[Category:Uploaded with mbc-harvester]]
    """.strip() % \
        (record.title, record.date, record.record_numeric_id, record.record_numeric_id, record.record_numeric_id)

    logger.info('Record metadata: %r', record)
    logger.info('Uploading "%s" ...', file_name)
    logger.info('File description: %s', file_desciption)


def main():
    logger = logging.getLogger('oai-harvester')
    logger.info('Using <%s> OAI endpoint',  OAI_ENDPOINT)

    harvester = Sickle(OAI_ENDPOINT)

    # https://www.mediawiki.org/wiki/Manual:Pywikibot/Create_your_own_script
    # https://doc.wikimedia.org/pywikibot/master/api_ref/index.html
    commons = pywikibot.Site()
    logger.info('pywikibot: %r', commons._siteinfo)

    # https://www.wbc.poznan.pl/dlibra/oai-pmh-repository.xml?verb=ListRecords&metadataPrefix=oai_dc&set=rootCollection:wbc:ContemporaryRegionalMagazines
    set_name = 'MDL:CD:Warwilustrpras'

    for idx, record in enumerate(get_set(harvester, set_name)):
        logger.info('---')
        logger.info('Record #%d found: %r', idx+1, record)

        # oai:mbc.cyfrowemazowsze.pl:59990
        try:
            # oai:mbc.cyfrowemazowsze.pl:59990 -> mbc.cyfrowemazowsze.pl
            source_id = str(record.header.identifier).split(':')[1]

            record_meta = RecordMeta(
                record_id=record.header.identifier,
                source_id=source_id,
                title=record.metadata['title'][0],
                date=str(record.metadata['date'][0]).strip('[]'),
                content_url=get_content_url(record),
                tags=sorted(list(set(record.metadata['subject']))),
            )

            # logger.info('Raw metadata: %r', record.metadata)
            upload_to_commons(record=record_meta)

        except:
            logger.error('Exception', exc_info=True)
            pass

        # DEBUG
        if idx > 5:
            break


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
