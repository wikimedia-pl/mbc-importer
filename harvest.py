"""
List MBC sets
"""
import logging
import tempfile

import pywikibot

from sickle import Sickle
from dlibra import get_categories_for_record, get_content_url, get_medium_for_record, get_rdf_metadata, get_set, http_session, RecordMeta


# TODO: take these from env variables
DLIBRA_SERVER = 'https://mbc.cyfrowemazowsze.pl/'
# DLIBRA_SERVER = 'https://www.wbc.poznan.pl/'
OAI_ENDPOINT = f'{DLIBRA_SERVER}dlibra/oai-pmh-repository.xml'
UPLOAD_COMMENT = 'Importing MBC digital content'

# https://www.wbc.poznan.pl/dlibra/oai-pmh-repository.xml?verb=ListRecords&metadataPrefix=oai_dc&set=rootCollection:wbc:ContemporaryRegionalMagazines
OAI_SET_NAME = 'MDL:CD:Warwilustrpras'


START_FROM_ITEM = 0
# START_FROM_ITEM = 5005





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

        response = http_session.get(record.content_url)

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

    # skip "certificate verify failed: unable to get local issuer certificate"
    harvester.request_args = {
        'verify': http_session.verify
    }

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

        break  # DEBUG

        # DEBUG
        # if idx > 75:
        #    break


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    main()
