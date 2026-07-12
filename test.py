import urllib.request, re, json, urllib.parse
req = urllib.request.Request('https://fragment.com/', headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req).read().decode('utf-8')
match = re.search(r'ajInit\(\{.*?"apiUrl":"\\/api\?hash=([a-z0-9]+)"', html)
if match:
    api_hash = match.group(1)
    url = f'https://fragment.com/api?hash={api_hash}'
    data = urllib.parse.urlencode({'query': 'yashil', 'method': 'searchUsernames'}).encode()
    req2 = urllib.request.Request(url, data=data, headers={'User-Agent': 'Mozilla/5.0', 'X-Requested-With': 'XMLHttpRequest'})
    try:
        res = urllib.request.urlopen(req2).read().decode('utf-8')
        print(res[:500])
    except Exception as e:
        print(e)
