import json

import requests
from flask import Flask

app = Flask(__name__)

with open('data.json') as f:
    DATA = json.loads(f.read())
HTML_BOILERPLATE = '''
<!doctype html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="X-UA-Compatible" content="ie=edge">
        <title>{title}Libris-Wikipedia-länkar</title>
    </head>
    <body><h1>Libris-Wikipedia-länkar</h1>{body}</body>
</html>
'''


@app.route('/')
def index():
    urls = [
        '/wiki/Mars (planet)',
        '/wiki/Ada Yonath',
        '/wiki/Jens Christian Skou',
    ]
    hrefs = list(map(
        lambda url: '<a href="{0}">{0}</a>'.format(url),
        urls,
    ))
    return HTML_BOILERPLATE.format(
        title='',
        body='''
<p>{hrefs}</p>
'''.format(
            hrefs='<br>'.join(hrefs),
        ),
    )


@app.route('/wiki/<title>')
def wiki(title):
    wiki_api_url = (
        'https://sv.wikipedia.org/w/api.php?action=query&formatversion=2&'
        'titles={title}&prop=pageterms|pageimages&format=json'
    ).format(
        title=title,
    )
    resp = requests.get(wiki_api_url)
    r_data = resp.json()

    page = r_data['query']['pages'][0]
    if 'missing' in page and page['missing']:
        return HTML_BOILERPLATE.format(title='Ingen sida', body='Ingen sida')

    title_wiki = page['title']
    desc = '<br>'.join(page['terms']['description']) \
        if 'description' in page['terms'] else ''
    img_src = page['thumbnail']['source']

    libris_urls = set()
    title_wiki_url_fmt = title.replace(' ', '_')
    for rel in DATA:
        if title_wiki_url_fmt in rel['uri_wikipedia']:
            libris_urls.add(rel['uri_libris'])
    libris_hrefs = list(map(
        lambda url: '<a href="{0}">{0}</a>'.format(url),
        libris_urls,
    ))

    return HTML_BOILERPLATE.format(
        title=title_wiki + ' - ',
        body='''
<h2>Wikipedia: {header}</h2>
<p>{desc}</p>
<img src="{img_src}">
<p>Källa: {source}</p>
<h3>Det här ämnet i Libris</h3>
<p>{libris_hrefs}</p>
'''.format(
            header=title_wiki,
            desc=desc,
            img_src=img_src,
            source='<a href="https://sv.wikipedia.org/wiki/{0}">'
            'https://sv.wikipedia.org/wiki/{0}</a>'.format(title_wiki_url_fmt),
            libris_hrefs='<br>'.join(libris_hrefs),
        ),
    )


@app.route('/libris/<uri>')
def libris():
    return 'Hello World!'
