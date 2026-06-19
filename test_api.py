import urllib.request, json
try:
    req = urllib.request.urlopen('http://localhost:8005/api/config/bot')
    data = json.loads(req.read())
    for section in data['data']['sections']:
        for field in section['fields']:
            print(f"Key: {field['key']}, Label: {field.get('label')}")
            print(f"Desc: {field.get('description')}")
except Exception as e:
    print(e)