import json
import requests

from flask import Flask, abort

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


libreq = requests.session()
libreq.headers.update({'Accept': 'application/ld+json'})


@app.route('/')
def index():
    wiki_urls = get_wiki_urls()
    libris_urls = get_libris_urls()
    return HTML_BOILERPLATE.format(
        title='',
        body='''
<h3>Wikipedia-artiklar</h3>
<p>{wiki_urls}</p>
<h3>Libris-resurser</h3>
<p>{libris_urls}</p>
'''.format(
            wiki_urls='<br>'.join(wiki_urls),
            libris_urls='<br>'.join(libris_urls),
        ),
    )


def get_wiki_urls():
    base = 'https://sv.wikipedia.org/wiki/'
    urls = set([e['uri_wikipedia'][len(base):] for e in DATA])
    return list(map(
        lambda url: '<a href="/wiki/{0}">{0}</a>'.format(url),
        sorted(list(urls)),
    ))


def get_libris_urls():
    urls = set([e['uri_libris'] for e in DATA])
    return list(map(
        lambda url: '<a href="/libris/{0}">{0}</a>'.format(url),
        sorted(list(urls)),
    ))


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
    img_name = page['pageimage']

    img_response = requests.get(
        'https://commons.wikimedia.org/w/api.php?action=query&format=json&'
        'prop=imageinfo&titles=File:{img_name}&iiprop=url'.format(
            img_name=img_name,
        )).json()
    img_id = list(img_response['query']['pages'].keys())[0]
    img_src = img_response['query']['pages'][img_id]['imageinfo'][0]['url']

    libris_urls = set()
    title_wiki_url_fmt = title.replace(' ', '_')
    for rel in DATA:
        if title_wiki_url_fmt in rel['uri_wikipedia']:
            libris_urls.add(rel['uri_libris'])
    libris_hrefs = list(map(
        lambda url: '<a href="/libris/{0}">/libris/{0}</a>'.format(url),
        libris_urls,
    ))

    return HTML_BOILERPLATE.format(
        title=title_wiki + ' - ',
        body='''
<h2>Wikipedia: {header}</h2>
<p>{desc}</p>
<img src="{img_src}" style="max-width:300px;">
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


@app.route('/libris')
def list_libris_resources():
    links = create_libris_links()
    return HTML_BOILERPLATE.format(
        title='Libris-resurser',
        body='''
<h2>Libris-resurser</h2>
<p>{libris_hrefs}</p>
'''.format(
            libris_hrefs='<br>'.join(links),
        ),
    )


def create_libris_links():
    links = set()
    for elem in DATA:
        link = '<a href="/libris/{}">{}</a>'
        libris_uri = elem['uri_libris']
        links.add(link.format(libris_uri, libris_uri))
    return sorted(list(links))


@app.route('/libris/<path:uri>')
def libris(uri):
    print(uri)
    lookup_url = 'https://libris-qa.kb.se/{}/data.jsonld'

    res = libreq.get(lookup_url.format(uri))
    if res.status_code != 200:
        abort(res.status_code)
    data = res.json()
    title = data['@graph'][1]['prefLabel']
    relations = get_libris_relations(data)
    bib_posts = []
    for rel in relations['items']:
        main_title = 'unknown'
        if 'hasTitle' in rel and 'mainTitle' in rel['hasTitle'][0]:
            main_title = rel['hasTitle'][0]['mainTitle']
        bib_posts.append('<a href="{}">{}</a>'.format(rel['@id'], main_title))
    wiki_links = []
    for elem in DATA:
        if elem['uri_libris'] == uri:
            link = elem['uri_wikipedia']
            wiki_title = link\
                .replace('https://sv.wikipedia.org/wiki/', '')\
                .replace('_', ' ')
            wiki_links.append('<a href="/wiki/{0}">/wiki/{0}</a>'.format(
                wiki_title
            ))
    return HTML_BOILERPLATE.format(
        title=title + ' - ',
        body='''
<h2>Libris: {header}</h2>
<p>{desc}</p>
<h3>Wikipedia-artiklar</h3>
<p>{wiki_links}</p>
<h3>Libris-poster</h3>
<p>{bib_posts}</p>
'''.format(
            header=uri,
            desc=title,
            wiki_links='<br>'.join(wiki_links),
            bib_posts='<br>'.join(bib_posts),
        ),
    )


libris_search_url = 'https://libris-qa.kb.se/find.json'


def get_libris_relations(data):
    main_entity = data['@graph'][0]['mainEntity']['@id']
    post_type = data['@graph'][1]['@type']
    query = build_libris_reverse_query(main_entity, post_type)
    res = libreq.get(libris_search_url, params=query)
    if res.status_code != 200:
        abort(res.status_code)
    return res.json()


def build_libris_reverse_query(entity_id, post_type):
    query = {}
    if post_type == 'Topic':
        query['instanceOf.subject.@id'] = entity_id

    return query
