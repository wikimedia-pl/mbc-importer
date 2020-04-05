"""
List MBC sets
"""
import logging
import requests

from typing import List

from lxml.etree import ElementBase
from sickle import Sickle, models, OAIResponse

DLIBRA_SERVER = 'http://mbc.cyfrowemazowsze.pl/'
# DLIBRA_SERVER = 'https://www.wbc.poznan.pl/'
OAI_ENDPOINT = f'{DLIBRA_SERVER}dlibra/oai-pmh-repository.xml'


def main():
    logger = logging.getLogger('oai-harvester')
    logger.info('Using <%s> OAI endpoint',  OAI_ENDPOINT)

    harvester = Sickle(OAI_ENDPOINT)
    # print(harvester)
    #
    # for idx, set_ in enumerate(harvester.ListSets()):
    #     logger.info('Set #%d found: %r', idx+1, set_)

    resource_id = 'oai:mbc.cyfrowemazowsze.pl:43271'

    # https://www.wbc.poznan.pl/dlibra/oai-pmh-repository.xml?verb=GetRecord&metadataPrefix=oai_dc&identifier=oai:www.wbc.poznan.pl:168305
    # <setSpec>MDL:CD:Warwilustrpras</setSpec>
    # record = harvester.GetRecord(metadataPrefix='oai_dc', identifier=resource_id)
    # print(record)

    # https://www.wbc.poznan.pl/dlibra/oai-pmh-repository.xml?verb=ListRecords&metadataPrefix=oai_dc&set=rootCollection:wbc:ContemporaryRegionalMagazines
    set_name = 'MDL:CD:Warwilustrpras'

    records = harvester.ListRecords(metadataPrefix='oai_dc', set=set_name)  # type: List[models.Record]

    for idx, record in enumerate(records):
        logger.info('---')
        logger.info('Record #%d found: %r', idx+1, record)

        # oai:mbc.cyfrowemazowsze.pl:59990
        try:
            record_id = int(str(record.header.identifier).split(':')[-1])

            record_meta = dict(
                record_id=record_id
            )

            # enumerate metadata
            for key, value in record:
                logger.debug(' > %r', (key, value))

                # e.g. http://mbc.cyfrowemazowsze.pl/Content/59991
                if key == 'identifier':
                    content_xml_url = value[0]
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
                    record_meta['content_url'] = f'{content_xml_url}/{image_node.text}'
                    logger.debug('Content URL: <%s>', record_meta['content_url'])

            logger.info('Record metadata: %r', record_meta)

        except:
            logger.error('Exception', exc_info=True)
            pass

        # DEBUG
        if idx > 5:
            break

    #http://mbc.cyfrowemazowsze.pl/dlibra/oai-pmh-repository.xml?verb=GetRecord&metadataPrefix=oai_dc&identifier=oai:mbc.cyfrowemazowsze.pl:61991
    # http://mbc.cyfrowemazowsze.pl/Content/61991/PresentationData.xml
    # <![CDATA[ 00066229_0000.jpg ]]>

    # http://mbc.cyfrowemazowsze.pl/Content/61991/00066224_0000.jpg


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
