# https://www.mediawiki.org/wiki/Manual:Pywikibot/user-config.py
mylang = 'commons'
family = 'commons'
usernames['commons']['commons'] = 'Mazovian_Digital_Library_Upload'

upload_to_commons = True
maxthrottle = 2

console_encoding = 'utf-8'

password_file = 'user-password.py'

# https://doc.wikimedia.org/pywikibot/stable/api_ref/pywikibot.config.html#settings-to-avoid-server-overload
# Maximum number of times to retry an API request before quitting.
max_retries = 1
# Minimum time to wait before resubmitting a failed API request.
retry_wait = 5
# Maximum time to wait before resubmitting a failed API request.
retry_max = 10
