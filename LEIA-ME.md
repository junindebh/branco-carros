# Site da Branco Veículos

Este projeto gera o site a partir de pastas e arquivos de texto simples. Você cadastra o carro, salva no GitHub, e o site se atualiza sozinho em cerca de 1 a 2 minutos. Cada veículo ganha uma página própria, que o Google consegue encontrar.

## O que tem em cada pasta

| Pasta ou arquivo | Para que serve |
|---|---|
| `estoque/` | Uma pasta por veículo, com o `carro.txt` e as fotos |
| `config.json` | Dados da loja: telefones, endereço, horários, domínio |
| `loja/fachada.jpg` | Foto da fachada usada no site |
| `templates/`, `assets/`, `build.py` | O "motor" do site. Normalmente não precisa mexer |
| `.github/workflows/publicar.yml` | Faz a publicação automática no GitHub |

## Cadastrar um carro novo

1. No GitHub, abra o repositório e entre na pasta `estoque`.
2. Clique em **Add file > Upload files**.
3. Arraste a **pasta do carro** já pronta, com o `carro.txt` e as fotos dentro. Veja abaixo como montar.
4. Clique em **Commit changes**. Pronto: em 1 a 2 minutos o carro aparece no site.

### Como montar a pasta do carro

- **Nome da pasta:** só letras minúsculas sem acento, números e hífen. Exemplo: `ranger-limited-2022`. Esse nome vira o endereço da página (`/carros/ranger-limited-2022/`), então escolha com cuidado e não troque depois.
- **Dentro da pasta:** o arquivo `carro.txt` e as fotos.
- **Dica:** copie a pasta `hilux-srx` e troque as informações e as fotos.

### O arquivo carro.txt

Cada linha é `campo: valor`. Linhas que começam com `#` são comentários.

| Campo | Exemplo | Observação |
|---|---|---|
| `nome` | `Ford Ranger Limited 3.2` | Obrigatório. Aparece como título |
| `marca` | `Ford` | |
| `modelo` | `Ranger Limited 3.2` | |
| `tipo` | `picape` | `picape`, `suv` ou `hatch` (hatches e sedãs) |
| `ano` | `2022/2023` | Fabricação/modelo, ou só um ano |
| `km` | `41.250` | Só números ou com ponto |
| `preco` | `289.900` | Em branco mostra "Consulte o valor" |
| `combustivel` | `Diesel` | |
| `cambio` | `Automático` | |
| `cor` | `Branca` | |
| `extras` | `Cabine=Dupla; Tração=4x4` | Pares `Nome=Valor` separados por `;` |
| `itens` | `Bancos de couro; Multimídia` | Separados por `;` |
| `descricao` | `Único dono. Revisada.` | Opcional. Use `\|` para separar parágrafos |
| `capa` | `02-lateral.jpg` | Foto usada no cartão da lista |
| `capa-y` | `56` | Altura do recorte da capa (0 = topo, 100 = base) |
| `destaque` | `sim` | Coloca o carro no início da lista |
| `status` | `disponivel` | Também aceita `vendido` e `oculto` |

Se um campo ficar em branco, o site mostra "Consulte".

### Fotos

- Use arquivos `.jpg`, `.jpeg`, `.png` ou `.webp`.
- **A ordem** é a ordem alfabética do nome do arquivo, então numere: `01-frente.jpg`, `02-lateral.jpg`.
- **A legenda** que aparece embaixo da foto vem do nome do arquivo: `06-bancos-dianteiros.jpg` vira "Bancos dianteiros".
- Tire de 6 a 10 fotos: frente, lateral, traseira, painel, bancos, porta-malas, motor.
- O site reduz as fotos sozinho, então pode enviar as originais do celular.

## Vender, esconder ou remover um carro

- **Vendido:** mude para `status: vendido`. O carro sai da lista e a página fica com o aviso "já foi vendido". O Google deixa de indexar essa página.
- **Esconder:** `status: oculto`. A página não é criada.
- **Apagar de vez:** apague a pasta do carro no GitHub.

Para editar um arquivo no GitHub: abra o `carro.txt`, clique no lápis, altere e clique em **Commit changes**.

## Tirar os carros de exemplo

As pastas `estoque/exemplo-...` são só para mostrar como o site fica. Antes de divulgar, faça uma das duas coisas:

- apague essas pastas; ou
- abra o `config.json` e mude `"mostrar_exemplos": true` para `false`.

As páginas de exemplo nunca entram no Google nem no `sitemap.xml`.

## Publicar no GitHub (primeira vez)

1. Crie uma conta no github.com e um repositório **público**, por exemplo `branco-veiculos`.
2. Envie todos os arquivos deste projeto para o repositório. Atenção: a pasta `.github` precisa ir junto, porque é ela que faz a publicação automática. Ela fica oculta em alguns sistemas. Se não conseguir enviar, clique em **Add file > Create new file**, digite o nome `.github/workflows/publicar.yml` e cole o conteúdo do arquivo.
3. Vá em **Settings > Pages**. Em **Source**, escolha **GitHub Actions**.
4. Abra a aba **Actions** e espere a publicação ficar verde. O endereço do site aparece em **Settings > Pages**.

## Domínio próprio

1. Registre o domínio em registro.br (um `.com.br` custa cerca de R$ 40 por ano).
2. Abra o `config.json` e troque `"dominio"` pelo endereço real, por exemplo `https://www.brancoveiculos.com.br`. Esse valor é usado no `sitemap.xml`, no `robots.txt` e nas informações para o Google.
3. No painel de DNS do Registro.br, crie:
   - para o `www`: um registro **CNAME** apontando para `SEU-USUARIO.github.io`;
   - para o endereço sem `www`: quatro registros **A** apontando para `185.199.108.153`, `185.199.109.153`, `185.199.110.153` e `185.199.111.153`.
4. No GitHub, em **Settings > Pages > Custom domain**, digite o domínio e salve. Quando o cadeado aparecer, marque **Enforce HTTPS**.

O DNS pode levar de alguns minutos a algumas horas para valer.

## Aparecer no Google

1. Cadastre o site no **Google Search Console** (gratuito) e envie o endereço `https://SEU-DOMINIO/sitemap.xml`.
2. Confirme o perfil da loja no **Google Meu Negócio** e coloque o link do site nele. Isso ajuda muito nas buscas locais, como "concessionária em Rolim de Moura".
3. O Google leva dias ou semanas para listar as páginas novas. Isso é normal.

## Testar no seu computador (opcional)

Precisa ter o Python instalado. No terminal, dentro da pasta do projeto:

```
pip install pillow
python build.py
```

Depois abra `_site/index.html` no navegador. O comando também avisa se algo estiver errado nas fichas dos carros.

## Limitações

- O simulador de financiamento é só uma estimativa e não consulta bancos.
- Os formulários não enviam e-mail: eles abrem o WhatsApp com a mensagem pronta.
- O site não tem painel de administração. O cadastro é feito pelo GitHub, como descrito acima.
