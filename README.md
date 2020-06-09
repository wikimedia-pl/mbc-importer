# mbc-harvester

A script harvesting [Mazowiecka Biblietka Cyfrowa collection"Warszawa w ilustracji prasowej XIX w."](http://mbc.cyfrowemazowsze.pl/dlibra/collectiondescription?dirids=231). Files are then uploaded on Wikimedia Commons.

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
