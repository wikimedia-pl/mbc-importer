"""
List MBC sets
"""
import logging
from sickle import Sickle

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
    for idx, record in enumerate(harvester.ListRecords(metadataPrefix='oai_dc', set=set_name)):
        logger.info('Record #%d found: %r', idx+1, record)

        for metadata in record:
            logger.info(' > %r', metadata)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
