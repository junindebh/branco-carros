#!/usr/bin/env python3
"""Gera o site da Branco Veículos.

Lê config.json e as pastas em estoque/ (uma pasta por veículo, com carro.txt e fotos)
e escreve o site pronto na pasta _site/. Veja o LEIA-ME.md.

Uso:  python build.py      (precisa do Pillow: pip install pillow)
"""
import datetime
import html
import json
import re
import shutil
import sys
import urllib.parse
from pathlib import Path

from PIL import Image, ImageOps

RAIZ = Path(__file__).resolve().parent
SAIDA = RAIZ / '_site'
EXT = {'.jpg', '.jpeg', '.png', '.webp'}
TIPOS = {'picape': 'Picape', 'suv': 'SUV', 'hatch': 'Hatch ou sedã'}
DIAS_SCHEMA = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
esc = html.escape
avisos = []

SVG_PICAPE = '<svg viewBox="0 0 240 100" fill="none" stroke="currentColor" stroke-width="3" stroke-linejoin="round" aria-hidden="true"><path d="M12 70V44h86l10-18h42l22 18 42 4c10 2 16 6 16 14v8z"/><path d="M114 31h30l16 13h-54z"/><circle cx="55" cy="70" r="14" fill="#0C1730"/><circle cx="190" cy="70" r="14" fill="#0C1730"/></svg>'
SVG_CARRO = '<svg viewBox="0 0 240 100" fill="none" stroke="currentColor" stroke-width="3" stroke-linejoin="round" aria-hidden="true"><path d="M14 70V54c0-6 4-9 14-10l40-4 22-18h66l32 20 28 6c8 2 14 6 14 14v8z"/><path d="M94 26h58l24 16H78z"/><circle cx="60" cy="70" r="14" fill="#0C1730"/><circle cx="184" cy="70" r="14" fill="#0C1730"/></svg>'

cfg = json.loads((RAIZ / 'config.json').read_text(encoding='utf-8'))
dominio = cfg.get('dominio', '').rstrip('/')
dominio_real = bool(dominio) and 'SEUDOMINIO' not in dominio
hoje = datetime.date.today().isoformat()


# ---------------------------------------------------------------- utilidades
def num(v):
    """Lê '58400', '58.400', '259.900' ou 'R$ 259.900,00' e devolve número (ou None)."""
    if not v:
        return None
    s = re.sub(r'[^\d,\.]', '', v)
    if not s:
        return None
    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    elif re.fullmatch(r'\d{1,3}(\.\d{3})+', s):
        s = s.replace('.', '')
    x = float(s)
    return int(x) if x == int(x) else x


def brl(v):
    s = f'{v:,.2f}'
    return 'R$ ' + s.replace(',', 'X').replace('.', ',').replace('X', '.')


def milhar(v):
    return f'{int(v):,}'.replace(',', '.')


def wa(msg):
    return 'https://wa.me/%s?text=%s' % (cfg['whatsapp'], urllib.parse.quote(msg))


def render(nome, ctx):
    txt = (RAIZ / 'templates' / nome).read_text(encoding='utf-8')

    def f(m):
        k = m.group(1)
        if k not in ctx:
            raise KeyError('%s: falta o campo %s' % (nome, k))
        return str(ctx[k])
    return re.sub(r'\{\{(\w+)\}\}', f, txt)


def lista(v):
    return [x.strip() for x in (v or '').split(';') if x.strip()]


def legenda(p):
    s = re.sub(r'^\d+[\s._-]*', '', p.stem).replace('-', ' ').replace('_', ' ').strip()
    return s[:1].upper() + s[1:] if s else ''


def abrir(p):
    return ImageOps.exif_transpose(Image.open(p)).convert('RGB')


def recorte(im, tw, th, ypct):
    w, h = im.size
    ar = tw / th
    if w / h > ar:
        cw, ch = int(h * ar), h
    else:
        cw, ch = w, int(w / ar)
    cy = h * ypct / 100
    top = int(min(max(cy - ch / 2, 0), h - ch))
    left = (w - cw) // 2
    return im.crop((left, top, left + cw, top + ch)).resize((tw, th), Image.LANCZOS)


def json_script(obj):
    return json.dumps(obj, ensure_ascii=False).replace('</', '<\\/')


# ---------------------------------------------------------------- estoque
def ler_carro(pasta):
    arq = pasta / 'carro.txt'
    if not arq.exists():
        avisos.append('%s: falta o arquivo carro.txt' % pasta.name)
        return None
    if not re.fullmatch(r'[a-z0-9-]+', pasta.name):
        avisos.append('%s: o nome da pasta deve ter só letras minúsculas sem acento, números e hífen' % pasta.name)
        return None
    d = {}
    for linha in arq.read_text(encoding='utf-8').splitlines():
        linha = linha.strip()
        if not linha or linha.startswith('#') or ':' not in linha:
            continue
        k, v = linha.split(':', 1)
        d[k.strip().lower()] = v.strip()
    if not d.get('nome'):
        avisos.append('%s: falta o campo nome' % pasta.name)
        return None
    status = (d.get('status') or 'disponivel').lower()
    if status == 'oculto':
        return None
    tipo = (d.get('tipo') or 'hatch').lower()
    if tipo not in TIPOS:
        avisos.append('%s: tipo "%s" não existe, usei hatch (use picape, suv ou hatch)' % (pasta.name, tipo))
        tipo = 'hatch'
    fab = mod = None
    m = re.match(r'\s*(\d{4})(?:\s*/\s*(\d{4}))?', d.get('ano', ''))
    if m:
        fab = int(m.group(1))
        mod = int(m.group(2) or m.group(1))
    nome = d['nome']
    marca = d.get('marca') or nome.split()[0]
    modelo = d.get('modelo') or nome[len(marca):].strip() or nome
    extras = []
    for par in lista(d.get('extras')):
        if '=' in par:
            a, b = par.split('=', 1)
            extras.append((a.strip(), b.strip()))
    fotos_src = sorted(p for p in pasta.iterdir()
                       if p.suffix.lower() in EXT and not p.stem.lower().startswith('capa'))
    capa_src = None
    if d.get('capa') and (pasta / d['capa']).exists():
        capa_src = pasta / d['capa']
    else:
        for p in pasta.iterdir():
            if p.suffix.lower() in EXT and p.stem.lower().startswith('capa'):
                capa_src = p
        if capa_src is None and fotos_src:
            capa_src = fotos_src[0]
    return {
        'id': pasta.name, 'pasta': pasta, 'nome': nome, 'marca': marca, 'modelo': modelo, 'tipo': tipo,
        'fab': fab, 'mod': mod, 'km': num(d.get('km')), 'preco': num(d.get('preco')),
        'comb': d.get('combustivel') or None, 'cambio': d.get('cambio') or None, 'cor': d.get('cor') or None,
        'extras': extras, 'itens': lista(d.get('itens')), 'descricao': d.get('descricao') or '',
        'exemplo': (d.get('exemplo') or '').lower() in ('sim', 's', 'true', '1'),
        'destaque': (d.get('destaque') or '').lower() in ('sim', 's', 'true', '1'),
        'vendido': status == 'vendido',
        'fotos_src': fotos_src, 'capa_src': capa_src,
        'capa_y': float(d.get('capa-y') or 56),
        'fotos': [], 'capa': False,
    }


def processar_fotos(c):
    destino = SAIDA / 'carros' / c['id']
    destino.mkdir(parents=True, exist_ok=True)
    for i, p in enumerate(c['fotos_src'], 1):
        im = abrir(p)
        g = im.copy()
        g.thumbnail((900, 1200), Image.LANCZOS)
        g.save(destino / ('foto-%d.jpg' % i), quality=76, optimize=True, progressive=True)
        m = im.copy()
        m.thumbnail((180, 240), Image.LANCZOS)
        m.save(destino / ('mini-%d.jpg' % i), quality=70, optimize=True)
        c['fotos'].append({'full': 'foto-%d.jpg' % i, 'mini': 'mini-%d.jpg' % i,
                           'leg': legenda(p), 'w': g.size[0], 'h': g.size[1]})
    if c['capa_src']:
        im = abrir(c['capa_src'])
        recorte(im, 640, 360, c['capa_y']).save(destino / 'capa.jpg', quality=78, optimize=True)
        recorte(im, 1200, 630, c['capa_y']).save(destino / 'og.jpg', quality=80, optimize=True)
        c['capa'] = True


# ---------------------------------------------------------------- HTML dos cartões e páginas
def li(s):
    return '<li>%s</li>' % s


def msg_carro(c):
    ano = ' %d/%d' % (c['fab'], c['mod']) if c['fab'] else ''
    return 'Olá! Tenho interesse no veículo %s%s que vi no site da Branco Veículos. Ainda está disponível?' % (c['nome'], ano)


def cartao(c, base, pos):
    href = '%scarros/%s/' % (base, c['id'])
    if c['capa']:
        capa = '<img src="%scapa.jpg" alt="" width="640" height="360" loading="lazy">' % href
    else:
        capa = SVG_PICAPE if c['tipo'] == 'picape' else SVG_CARRO
    if c['exemplo']:
        tag = '<span class="tag">Exemplo</span>' + ('' if c['capa'] else '<span class="soon">Foto em breve</span>')
    elif c['fotos']:
        tag = '<span class="tag">%d fotos</span>' % len(c['fotos'])
    else:
        tag = ''
    l1 = []
    if c['fab']:
        l1.append('Ano <b>%d/%d</b>' % (c['fab'], c['mod']))
    if c['km'] is not None:
        l1.append('<b>%s</b> km' % milhar(c['km']))
    l2 = [esc(x) for x in (c['comb'], c['cambio'], c['cor']) if x]
    preco = brl(c['preco']) if c['preco'] is not None else '<span class="consulte">Consulte o valor</span>'
    return (
        '<article class="car" data-tipo="%s" data-preco="%s" data-ano="%s" data-km="%s" data-pos="%d">'
        '<a class="thumb" href="%s" aria-label="Ver detalhes: %s">%s%s</a>'
        '<div class="car-body"><h3><a class="car-link" href="%s">%s</a></h3>%s<ul class="specs">%s</ul>'
        '<p class="price">%s</p>'
        '<div class="actions"><a class="btn btn-gold btn-sm" href="%s">Ver detalhes</a>'
        '<a class="btn btn-wa btn-sm" target="_blank" rel="noopener" href="%s"><svg><use href="#i-chat"/></svg>WhatsApp</a></div>'
        '</div></article>'
    ) % (
        c['tipo'], c['preco'] if c['preco'] is not None else '', c['mod'] or '', c['km'] if c['km'] is not None else '', pos,
        href, esc(c['nome']), capa, tag, href, esc(c['nome']),
        ('<ul class="specs">%s</ul>' % ''.join(map(li, l1))) if l1 else '', ''.join(map(li, l2)),
        preco, href, esc(wa(msg_carro(c))),
    )


def conteudo_carro(c, outros, base):
    fotos = c['fotos']
    if fotos:
        f0 = fotos[0]
        gal = (
            '<div class="gal" style="--ar:%d/%d;--arv:%.4f">'
            '<div class="viewer" id="g-viewer"><img id="g-img" src="%s" alt="%s" width="%d" height="%d" data-nome="%s">'
            '<button class="nav prev" id="g-prev" type="button" aria-label="Foto anterior">&#8249;</button>'
            '<button class="nav next" id="g-next" type="button" aria-label="Próxima foto">&#8250;</button>'
            '<span class="count" id="g-count">1 / %d</span></div>'
            '<p class="cap" id="g-cap">%s</p><div class="ths" id="g-ths" role="group" aria-label="Fotos do veículo">%s</div></div>'
        ) % (
            f0['w'], f0['h'], f0['w'] / f0['h'], f0['full'],
            esc(c['nome'] + (': ' + f0['leg'] if f0['leg'] else '')), f0['w'], f0['h'], esc(c['nome']),
            len(fotos), esc(f0['leg']),
            ''.join(
                '<button class="th" type="button" data-full="%s" data-leg="%s" aria-label="Foto %d%s" aria-current="%s">'
                '<img src="%s" alt="" width="90" height="120" loading="lazy"></button>'
                % (f['full'], esc(f['leg']), i + 1, esc(': ' + f['leg']) if f['leg'] else '',
                   'true' if i == 0 else 'false', f['mini'])
                for i, f in enumerate(fotos)),
        )
    else:
        gal = '<div class="gal"><div class="viewer empty">%s<p>Fotos em breve</p></div></div>' % (
            SVG_PICAPE if c['tipo'] == 'picape' else SVG_CARRO)

    ano = '%d/%d' % (c['fab'], c['mod']) if c['fab'] else None
    km = '%s km' % milhar(c['km']) if c['km'] is not None else None
    consulte = lambda v: esc(v) if v else 'Consulte'
    linhas = [('Marca', c['marca']), ('Modelo', c['modelo']), ('Tipo', TIPOS[c['tipo']]), ('Ano', ano),
              ('Quilometragem', km), ('Combustível', c['comb']), ('Câmbio', c['cambio']), ('Cor', c['cor'])] + c['extras']
    tabela = ''.join('<tr><th scope="row">%s</th><td>%s</td></tr>' % (esc(a), consulte(b)) for a, b in linhas)
    fatos = ''.join('<div><dt>%s</dt><dd>%s</dd></div>' % (a, consulte(b))
                    for a, b in (('Ano', ano), ('Quilometragem', km), ('Câmbio', c['cambio']), ('Cor', c['cor'])))
    itens = ''
    if c['itens']:
        itens = ('<h2 class="h-sm">Itens do veículo</h2><ul class="items">%s</ul>'
                 '<p class="hint">A lista completa de equipamentos é confirmada pela equipe da loja.</p>'
                 % ''.join(li(esc(x)) for x in c['itens']))
    desc = ''.join('<p class="desc">%s</p>' % esc(p) for p in c['descricao'].split('|') if p.strip())
    avisos_html = ''
    if c['exemplo']:
        avisos_html += '<p class="notice"><span aria-hidden="true">&#9888;</span><span>Veículo de exemplo. As informações são ilustrativas.</span></p>'
    if c['vendido']:
        avisos_html += '<p class="notice"><span aria-hidden="true">&#9888;</span><span>Este veículo já foi vendido. Veja os que estão disponíveis no estoque.</span></p>'
    preco = brl(c['preco']) if c['preco'] is not None else 'Consulte o valor'
    sub = ('Valor sujeito a confirmação pela loja.' if c['preco'] is not None
           else 'Fale com a equipe pelo WhatsApp para saber o preço e as condições.')
    if c['vendido']:
        cta = '<a class="btn btn-gold" href="%s#estoque">Ver estoque disponível</a>' % base
    else:
        cta = ('<a class="btn btn-wa" target="_blank" rel="noopener" href="%s"><svg><use href="#i-chat"/></svg>Tenho interesse</a>'
               '<a class="btn btn-line" href="%s#financiamento">Simular financiamento</a>') % (esc(wa(msg_carro(c))), base)
    tel = cfg['telefones'][0]
    outros_html = ''
    if outros:
        outros_html = ('<section class="also" aria-labelledby="tambem"><h2 class="h-sm" id="tambem">Veja também</h2><div class="grid">%s</div></section>'
                       % ''.join(cartao(o, base, i) for i, o in enumerate(outros)))
    return (
        '<nav class="crumbs" aria-label="Você está em"><a href="%s#estoque">&#8592; Voltar ao estoque</a>'
        '<span aria-hidden="true">/</span><span aria-current="page">%s</span></nav>'
        '<div class="detail">%s<div class="info-col"><p class="eyebrow">%s &middot; %s</p><h1>%s</h1>'
        '<p class="price-big">%s<small>%s</small></p>%s<div class="cta-row">%s</div>'
        '<p class="hint">Ou ligue: <a href="tel:+%s">%s</a></p><dl class="facts">%s</dl>%s'
        '<h2 class="h-sm">Ficha técnica</h2><table class="spec"><tbody>%s</tbody></table>%s</div></div>%s'
    ) % (base, esc(c['nome']), gal, esc(c['marca']), TIPOS[c['tipo']], esc(c['nome']), preco, sub, avisos_html, cta,
         tel['numero'], tel['exibir'], fatos, desc, tabela, itens, outros_html)


def head_extra(caminho, titulo, desc, og_img, ld=None):
    p = []
    if dominio_real:
        p.append('<link rel="canonical" href="%s/%s">' % (esc(dominio), caminho))
        p.append('<meta property="og:url" content="%s/%s">' % (esc(dominio), caminho))
        if og_img:
            p.append('<meta property="og:image" content="%s/%s">' % (esc(dominio), og_img))
    p.append('<meta property="og:type" content="website"><meta property="og:locale" content="pt_BR">'
             '<meta property="og:site_name" content="%s">' % esc(cfg['nome']))
    p.append('<meta property="og:title" content="%s"><meta property="og:description" content="%s">' % (esc(titulo), esc(desc)))
    p.append('<meta name="twitter:card" content="summary_large_image">')
    if ld:
        p.append('<script type="application/ld+json">%s</script>' % json_script(ld))
    return '\n'.join(p)


# ---------------------------------------------------------------- build
def main():
    if SAIDA.exists():
        shutil.rmtree(SAIDA)
    (SAIDA / 'assets').mkdir(parents=True)
    shutil.copy(RAIZ / 'assets' / 'site.css', SAIDA / 'assets' / 'site.css')
    shutil.copy(RAIZ / 'assets' / 'site.js', SAIDA / 'assets' / 'site.js')
    shutil.copy(RAIZ / 'loja' / 'fachada.jpg', SAIDA / 'assets' / 'fachada.jpg')
    (SAIDA / '.nojekyll').write_text('')

    carros = []
    for pasta in sorted((RAIZ / 'estoque').iterdir()):
        if pasta.is_dir():
            c = ler_carro(pasta)
            if c and (cfg.get('mostrar_exemplos', True) or not c['exemplo']):
                carros.append(c)
    for c in carros:
        processar_fotos(c)
    carros.sort(key=lambda c: (not c['destaque'], c['exemplo'], c['nome']))
    disponiveis = [c for c in carros if not c['vendido']]

    end = cfg['endereco']
    ig_url = 'https://www.instagram.com/' + cfg['instagram']
    mapa = 'https://www.google.com/maps/search/?api=1&query=' + urllib.parse.quote(
        '%s, %s, %s, %s' % (end['rua'], end['bairro'], end['cidade'], end['uf']))
    horarios_ord = [1, 2, 3, 4, 5, 6, 0]
    horarios_html = '\n'.join(
        '<tr data-dia="%d"><th scope="row">%s</th><td>%s</td></tr>' % (
            i, cfg['horarios'][i]['dia'],
            ('%s às %s' % tuple(cfg['horarios'][i]['h'])) if cfg['horarios'][i]['h'] else '<span class="closed">Fechado</span>')
        for i in horarios_ord)
    telefones_html = '\n'.join(
        '<p><a href="tel:+%s">%s</a>%s</p>' % (t['numero'], t['exibir'], ' (WhatsApp)' if t.get('whatsapp') else '')
        for t in cfg['telefones'])
    dados = json_script({'whatsapp': cfg['whatsapp'], 'horarios': cfg['horarios']})
    msg_home = 'Olá! Vim pelo site da Branco Veículos e gostaria de mais informações.'

    def ctx_comum(base, wa_float):
        return {
            'base': base, 'wa_geral': esc(wa(msg_home)), 'wa_float': esc(wa_float),
            'wa_locadora': esc(wa('Olá! Gostaria de saber sobre a locadora: modelos disponíveis, períodos e valores.')),
            'instagram': cfg['instagram'], 'instagram_url': ig_url, 'ano': datetime.date.today().year,
            'dados_json': dados, 'simbolos': (RAIZ / 'templates' / '_simbolos.html').read_text(encoding='utf-8'),
            'end_rua': esc(end['rua']), 'end_bairro_cidade': esc('%s, %s - %s' % (end['bairro'], end['cidade'], end['uf'])),
            'cep': end['cep'], 'mapa_url': esc(mapa), 'email': esc(cfg['email']),
            'telefones_html': telefones_html, 'horarios_html': horarios_html, 'taxa': cfg.get('taxa_simulador', 2),
        }

    def pagina(modelo, base, wa_float, titulo, desc, robots, caminho, og_img, ld, extra):
        ctx = ctx_comum(base, wa_float)
        ctx.update(extra)
        ctx.update({'titulo': esc(titulo), 'descricao': esc(desc), 'robots': robots,
                    'head_extra': head_extra(caminho, titulo, desc, og_img, ld)})
        ctx['head'] = render('_head.html', ctx)
        ctx['topo'] = render('_topo.html', ctx)
        ctx['rodape'] = render('_rodape.html', ctx)
        return render(modelo, ctx)

    # ---- página inicial
    tipos_presentes = [t for t in TIPOS if any(c['tipo'] == t and not c['vendido'] for c in carros)]
    rot_chips = {'picape': 'Picapes', 'suv': 'SUVs', 'hatch': 'Hatches e sedãs'}
    chips = '\n        '.join('<button class="chip" type="button" data-f="%s" aria-pressed="false">%s</button>' % (t, rot_chips[t])
                              for t in tipos_presentes)
    aviso = ''
    if any(c['exemplo'] for c in disponiveis):
        aviso = ('<p class="notice" id="aviso-exemplo"><span aria-hidden="true">&#9888;</span>'
                 '<span>Os veículos marcados como Exemplo são ilustrativos e serão trocados pelo estoque real da loja.</span></p>')
    cards = '\n'.join(cartao(c, '', i) for i, c in enumerate(disponiveis))
    desc_home = ('Compra, venda, troca, financiamento e locadora de veículos em Rolim de Moura, Rondônia. '
                 'Veja o estoque e fale pelo WhatsApp. %s.' % end['rua'])
    ld_home = {
        '@context': 'https://schema.org', '@type': 'AutoDealer', 'name': cfg['nome'],
        'description': 'Compra, venda, troca, financiamento e locadora de veículos em Rolim de Moura, Rondônia.',
        'telephone': '+' + cfg['telefones'][0]['numero'], 'email': cfg['email'],
        'address': {'@type': 'PostalAddress', 'streetAddress': end['rua'], 'addressLocality': end['cidade'],
                    'addressRegion': end['uf'], 'postalCode': end['cep'], 'addressCountry': 'BR'},
        'areaServed': {'@type': 'City', 'name': end['cidade']},
        'openingHoursSpecification': [
            {'@type': 'OpeningHoursSpecification', 'dayOfWeek': DIAS_SCHEMA[i], 'opens': h['h'][0], 'closes': h['h'][1]}
            for i, h in enumerate(cfg['horarios']) if h['h']],
        'sameAs': [ig_url],
    }
    if dominio_real:
        ld_home['url'] = dominio + '/'
    (SAIDA / 'index.html').write_text(pagina(
        'home.html', '', wa(msg_home), 'Branco Veículos | Carros em Rolim de Moura - RO', desc_home,
        'index, follow, max-image-preview:large', '', 'assets/fachada.jpg', ld_home,
        {'cards': cards, 'chips': chips, 'aviso_exemplo': aviso}), encoding='utf-8')

    # ---- uma página por veículo
    for c in carros:
        base = '../../'
        outros = sorted((o for o in disponiveis if o['id'] != c['id']),
                        key=lambda o: (o['tipo'] != c['tipo'], o['exemplo'], o['nome']))[:3]
        ano = ' %d/%d' % (c['fab'], c['mod']) if c['fab'] else ''
        titulo = '%s%s | Branco Veículos - Rolim de Moura' % (c['nome'], ano)
        partes = [x for x in (('%d/%d' % (c['fab'], c['mod'])) if c['fab'] else None,
                              ('%s km' % milhar(c['km'])) if c['km'] is not None else None,
                              c['cambio'], c['cor']) if x]
        desc = '%s%s%s. Veja fotos e ficha técnica na Branco Veículos, Rolim de Moura - RO.' % (
            c['nome'], ': ' if partes else '', ', '.join(partes))
        indexar = not c['exemplo'] and not c['vendido']
        ld = None
        if indexar:
            ld = {'@context': 'https://schema.org', '@type': 'Car', 'name': c['nome'],
                  'brand': {'@type': 'Brand', 'name': c['marca']}, 'model': c['modelo'], 'bodyType': TIPOS[c['tipo']]}
            if c['cor']: ld['color'] = c['cor']
            if c['cambio']: ld['vehicleTransmission'] = c['cambio']
            if c['comb']: ld['fuelType'] = c['comb']
            if c['mod']: ld['vehicleModelDate'] = str(c['mod'])
            if c['km'] is not None:
                ld['mileageFromOdometer'] = {'@type': 'QuantitativeValue', 'value': c['km'], 'unitCode': 'KMT'}
            if dominio_real:
                ld['url'] = '%s/carros/%s/' % (dominio, c['id'])
                if c['fotos']:
                    ld['image'] = ['%s/carros/%s/%s' % (dominio, c['id'], f['full']) for f in c['fotos']]
            if c['preco'] is not None:
                ld['offers'] = {'@type': 'Offer', 'price': c['preco'], 'priceCurrency': 'BRL',
                                'availability': 'https://schema.org/InStock',
                                'seller': {'@type': 'AutoDealer', 'name': cfg['nome']}}
        pasta = SAIDA / 'carros' / c['id']
        pasta.mkdir(parents=True, exist_ok=True)
        (pasta / 'index.html').write_text(pagina(
            'carro.html', base, wa(msg_carro(c)), titulo, desc,
            'index, follow, max-image-preview:large' if indexar else 'noindex, follow',
            'carros/%s/' % c['id'], ('carros/%s/og.jpg' % c['id']) if c['capa'] else 'assets/fachada.jpg', ld,
            {'conteudo': conteudo_carro(c, outros, base)}), encoding='utf-8')

    # ---- sitemap, robots, domínio
    urls = [''] + ['carros/%s/' % c['id'] for c in disponiveis if not c['exemplo']]
    base_url = dominio if dominio else 'https://www.SEUDOMINIO.com.br'
    (SAIDA / 'sitemap.xml').write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
        ''.join('  <url><loc>%s/%s</loc><lastmod>%s</lastmod></url>\n' % (base_url, u, hoje) for u in urls) +
        '</urlset>\n', encoding='utf-8')
    (SAIDA / 'robots.txt').write_text('User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n' % base_url, encoding='utf-8')
    if dominio_real:
        (SAIDA / 'CNAME').write_text(urllib.parse.urlparse(dominio).netloc + '\n', encoding='utf-8')
    else:
        avisos.append('config.json: o campo "dominio" ainda é o de exemplo. Troque pelo endereço real antes de publicar.')

    reais = [c for c in disponiveis if not c['exemplo']]
    print('Site gerado em _site/: %d veículo(s) na lista (%d real, %d exemplo), %d vendido(s).' % (
        len(disponiveis), len(reais), len(disponiveis) - len(reais), len(carros) - len(disponiveis)))
    for a in avisos:
        print('AVISO:', a)


if __name__ == '__main__':
    sys.exit(main())
