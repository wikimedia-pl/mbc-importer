# mbc-harvester

A script harvesting [Mazowiecka Biblietka Cyfrowa collection"Warszawa w ilustracji prasowej XIX w."](http://mbc.cyfrowemazowsze.pl/dlibra/collectiondescription?dirids=231). Files are then uploaded on Wikimedia Commons.

It can crawl any e-library that is powered by [OAI-compatible software](https://www.openarchives.org/), for instance [dLibra](https://dingo.psnc.pl/dlibra/).

[**Importer is executed**](https://github.com/wikimedia-pl/mbc-importer/actions/workflows/do-import.yml) via GitHub Actions cross **twice a week** - at 7:00 AM every Monday and Thursday.

## Install

Set up Python env.

```
virtualenv env -ppython38
. env/bin/activate
pip install -r requirements.txt
```

Set up account that will used for uploads.

```
$ cat user-password.py 
('commons', 'commons', 'Mazovian_Digital_Library_Upload', 'XXX')
```

## Run

```
python harvest.py
```

## GitHub Actions

You need to set up the following secrets in order to run the importer as a cron-triggered action:

* `HTTP_PROXY` (e.g. `socks5://example.com:12345`)
* `PYWIKIBOT_USERNAME`
* `PYWIKIBOT_PASSWORD`
