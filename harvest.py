"""
List MBC sets
"""
import json
import logging
import requests

from typing import List

from lxml.etree import ElementBase
from sickle import Sickle, models, OAIResponse

DLIBRA_SERVER = 'http://mbc.cyfrowemazowsze.pl/'
# DLIBRA_SERVER = 'https://www.wbc.poznan.pl/'
OAI_ENDPOINT = f'{DLIBRA_SERVER}dlibra/oai-pmh-repository.xml'


def get_set(instance: Sickle, set_name: str) -> List[models.Record]:
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


def main():
    logger = logging.getLogger('oai-harvester')
    logger.info('Using <%s> OAI endpoint',  OAI_ENDPOINT)

    harvester = Sickle(OAI_ENDPOINT)
    # print(harvester)
    #
    # for idx, set_ in enumerate(harvester.ListSets()):
    #     logger.info('Set #%d found: %r', idx+1, set_)

    # resource_id = 'oai:mbc.cyfrowemazowsze.pl:43271'

    # https://www.wbc.poznan.pl/dlibra/oai-pmh-repository.xml?verb=GetRecord&metadataPrefix=oai_dc&identifier=oai:www.wbc.poznan.pl:168305
    # <setSpec>MDL:CD:Warwilustrpras</setSpec>
    # record = harvester.GetRecord(metadataPrefix='oai_dc', identifier=resource_id)
    # print(record)

    # https://www.wbc.poznan.pl/dlibra/oai-pmh-repository.xml?verb=ListRecords&metadataPrefix=oai_dc&set=rootCollection:wbc:ContemporaryRegionalMagazines
    set_name = 'MDL:CD:Warwilustrpras'

    for idx, record in enumerate(get_set(harvester, set_name)):
        logger.info('---')
        logger.info('Record #%d found: %r', idx+1, record)

        # oai:mbc.cyfrowemazowsze.pl:59990
        try:
            # oai:mbc.cyfrowemazowsze.pl:59990 -> mbc.cyfrowemazowsze.pl
            source_id = str(record.header.identifier).split(':')[1]

            record_meta = dict(
                record_id=record.header.identifier,
                source_id=source_id,
                title=record.metadata['title'][0],
                content_url=get_content_url(record),
                tags=sorted(list(set(record.metadata['subject']))),
            )

            logger.info('Record metadata: %s', json.dumps(record_meta, indent=True))

        except:
            logger.error('Exception', exc_info=True)
            pass

        # DEBUG
        # if idx > 5:
        #     break


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
