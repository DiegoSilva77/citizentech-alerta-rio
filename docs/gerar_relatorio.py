"""
Gera o relatório em PDF (docs/Relatorio_AlertaRio.pdf).

Uso (na raiz do projeto, Windows):
    pip install reportlab pillow
    python docs/gerar_relatorio.py

Preencha ALUNO e RM abaixo antes de gerar.
Este script não faz parte do sistema; por isso o reportlab não está no requirements.txt.
"""
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle)
from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String

ALUNO = "Diego Araujo Silva"
RM = "573684"

PASTA = Path(__file__).resolve().parent
SAIDA = sys.argv[1] if len(sys.argv) > 1 else str(PASTA / "Relatorio_AlertaRio.pdf")
IMG = sys.argv[2] if len(sys.argv) > 2 else str(PASTA / "painel.png")

pdfmetrics.registerFont(TTFont("Segoe", r"C:\Windows\Fonts\segoeui.ttf"))
pdfmetrics.registerFont(TTFont("Segoe-B", r"C:\Windows\Fonts\segoeuib.ttf"))
pdfmetrics.registerFont(TTFont("Mono", r"C:\Windows\Fonts\consola.ttf"))
from reportlab.lib.fonts import addMapping
addMapping("Segoe", 0, 0, "Segoe"); addMapping("Segoe", 1, 0, "Segoe-B")
addMapping("Segoe", 0, 1, "Segoe"); addMapping("Segoe", 1, 1, "Segoe-B")

AZUL = colors.HexColor("#13497b"); AZUL_CLARO = colors.HexColor("#e0f2fe"); AGUA = colors.HexColor("#0ea5e9")
CINZA = colors.HexColor("#5b6b80"); BORDA = colors.HexColor("#cbd5e1"); FUNDO = colors.HexColor("#f1f5f9")
VERDE = colors.HexColor("#16a34a"); AMBAR = colors.HexColor("#d97706"); VERM = colors.HexColor("#dc2626")

base = ParagraphStyle("base", fontName="Segoe", fontSize=8.6, leading=11.2, textColor=colors.HexColor("#0f172a"))
corpo = ParagraphStyle("corpo", parent=base, spaceAfter=3)
h1 = ParagraphStyle("h1", parent=base, fontName="Segoe-B", fontSize=17, leading=20, textColor=AZUL)
sub = ParagraphStyle("sub", parent=base, fontSize=8.5, textColor=CINZA)
h2 = ParagraphStyle("h2", parent=base, fontName="Segoe-B", fontSize=10.5, leading=13, textColor=AZUL, spaceBefore=6, spaceAfter=3)
cel = ParagraphStyle("cel", parent=base, fontSize=7.8, leading=9.8)
celb = ParagraphStyle("celb", parent=cel, fontName="Segoe-B", textColor=colors.white)
legenda = ParagraphStyle("leg", parent=base, fontSize=7, textColor=CINZA, alignment=TA_CENTER)
ref = ParagraphStyle("ref", parent=base, fontSize=7.2, leading=9, textColor=CINZA)


def P(t, s=corpo):
    return Paragraph(t, s)


def tabela(linhas, larguras, cor=AZUL):
    dados = [[Paragraph(str(c), celb if i == 0 else cel) for c in linha] for i, linha in enumerate(linhas)]
    t = Table(dados, colWidths=larguras, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), cor),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, FUNDO]),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDA),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def caixa(d, x, y, w, h, titulo, linha2, cor):
    d.add(Rect(x, y, w, h, rx=5, ry=5, fillColor=cor, strokeColor=AZUL, strokeWidth=0.8))
    d.add(String(x + w / 2, y + h - 12, titulo, fontName="Segoe-B", fontSize=7.8, textAnchor="middle", fillColor=AZUL))
    d.add(String(x + w / 2, y + 7, linha2, fontName="Segoe", fontSize=6.6, textAnchor="middle", fillColor=CINZA))


def seta(d, x1, y1, x2, y2, rot=""):
    d.add(Line(x1, y1, x2, y2, strokeColor=AZUL, strokeWidth=1))
    import math
    a = math.atan2(y2 - y1, x2 - x1); s = 5
    d.add(Polygon([x2, y2, x2 - s * math.cos(a - .4), y2 - s * math.sin(a - .4),
                   x2 - s * math.cos(a + .4), y2 - s * math.sin(a + .4)], fillColor=AZUL, strokeColor=AZUL))
    if rot:
        d.add(String((x1 + x2) / 2, (y1 + y2) / 2 + 3, rot, fontName="Segoe", fontSize=6.3, textAnchor="middle", fillColor=CINZA))


def diagrama():
    d = Drawing(17.4 * cm, 3.3 * cm)
    W, H = 3.3 * cm, 1.05 * cm
    caixa(d, 0, 52, W, H, "Sensores (ESP32 simul.)", "sensor_simulado.py", AZUL_CLARO)
    caixa(d, 4.6 * cm, 52, W, H, "Servidor UDP :5005", "HMAC + anti-replay", AZUL_CLARO)
    caixa(d, 9.3 * cm, 52, W, H, "MySQL 8 (SQL puro)", "4 tabelas, usuário mínimo", colors.HexColor("#ede9fe"))
    caixa(d, 0, 2, W, H, "Navegador", "HTML/CSS/JS, Leaflet, Chart.js", AZUL_CLARO)
    caixa(d, 4.6 * cm, 2, W, H, "Flask MVC (Controllers)", "Models · Views · Core", AZUL_CLARO)
    caixa(d, 9.3 * cm, 2, W, H, "Open-Meteo", "requests + JSON (cache)", colors.HexColor("#fff7ed"))
    caixa(d, 14 * cm, 27, W, H, "logs/alerta_rio.log", "data/hora · ação · resultado", colors.HexColor("#ecfdf5"))
    seta(d, W, 70, 4.6 * cm, 70, "UDP")
    seta(d, 4.6 * cm + W, 70, 9.3 * cm, 70, "INSERT")
    seta(d, W, 20, 4.6 * cm, 20, "HTTP/JSON")
    seta(d, 4.6 * cm + W, 20, 9.3 * cm, 20, "requests")
    seta(d, 6.25 * cm, 2 + H, 9.6 * cm, 52, "")
    seta(d, 9.3 * cm + W, 66, 14 * cm, 50, "")
    seta(d, 9.3 * cm + W, 20, 14 * cm, 36, "")
    return d


def rodape(canvas, doc):
    canvas.saveState()
    canvas.setFont("Segoe", 7); canvas.setFillColor(CINZA)
    canvas.drawString(1.6 * cm, 1 * cm, "Alerta Rio · Global Solution FIAP · CitizenTech · Coding for Security")
    canvas.drawRightString(A4[0] - 1.6 * cm, 1 * cm, f"Página {doc.page}")
    canvas.setStrokeColor(AGUA); canvas.setLineWidth(3)
    canvas.line(0, A4[1] - 3, A4[0], A4[1] - 3)
    canvas.restoreState()


doc = SimpleDocTemplate(SAIDA, pagesize=A4, leftMargin=1.6 * cm, rightMargin=1.6 * cm, topMargin=1.3 * cm,
                        bottomMargin=1.5 * cm, title="Alerta Rio - Relatório Global Solution",
                        author=ALUNO.strip("_ ") or "Alerta Rio", subject="CitizenTech - monitoramento comunitário de enchentes")
LW = A4[0] - 3.2 * cm
s = []

s.append(P("Alerta Rio: monitoramento comunitário de enchentes", h1))
s.append(P(f"Global Solution FIAP · CitizenTech · Coding for Security &nbsp;|&nbsp; Aluno: {ALUNO} "
           f"&nbsp; RM: {RM} &nbsp;|&nbsp; Novembro/2026", sub))
s.append(Spacer(1, 6))

# 1. Problema
s.append(P("1. Problema, cidadão e evidência", h2))
s.append(P("<b>Problema:</b> em áreas ribeirinhas, o aviso de enchente chega tarde ou de forma genérica (\"risco alto no "
           "estado\"). O morador não sabe <b>qual arroio</b> está subindo, <b>quanto tempo</b> tem e <b>para onde ir</b>. "
           "<b>Evidência (dado público):</b> nas enchentes de maio de 2024 no Rio Grande do Sul, o boletim da Defesa Civil RS "
           "de 03/06/2024 registrou <b>475 municípios afetados, cerca de 2,39 milhões de pessoas atingidas, 579 mil "
           "desalojados e 172 mortes</b>. Relatos da imprensa e de moradores mostraram famílias surpreendidas pela água "
           "dentro de casa e pessoas que se recusaram a sair por não poderem levar seus animais."))
s.append(P("<b>Cidadão beneficiado:</b> famílias que moram perto de arroios, rios e encostas, sobretudo idosos, pessoas "
           "com deficiência e tutores de animais. <b>Ecossistema:</b> moradores (consultam o painel), lideranças comunitárias "
           "e voluntários (instalam e mantêm os sensores nas pontes), Defesa Civil (operador que cadastra sensores e abrigos), "
           "abrigos como escolas, ginásios e igrejas (informam vagas, acessibilidade e se aceitam pets) e a Open-Meteo "
           "(previsão de chuva aberta)."))

# 2. ODS
s.append(P("2. Objetivos de Desenvolvimento Sustentável", h2))
s.append(tabela([
    ["ODS", "Meta", "Como o Alerta Rio contribui"],
    ["<b>11</b> · Cidades e comunidades sustentáveis", "11.5: reduzir mortes e pessoas afetadas por catástrofes, "
     "inclusive as relacionadas à água", "Alerta local e antecipado por ponto do rio; mapa de abrigos com vagas livres, "
     "acessibilidade e aceitação de pets"],
    ["<b>13</b> · Ação contra a mudança do clima", "13.1: reforçar a resiliência e a capacidade de adaptação a riscos "
     "climáticos", "Cruza nível do rio com a previsão de chuva; histórico de leituras e alertas que serve de base para "
     "cobrar obras e planejar a resposta"],
], [3.6 * cm, 5.4 * cm, LW - 9 * cm]))

# 3. Solução
s.append(P("3. Como a solução funciona", h2))
s.append(P("Sensores de nível (simulados em Python, representando ESP32 + sensor ultrassônico) enviam leituras "
           "<b>assinadas</b> por <b>socket UDP</b>. O servidor UDP valida o pacote, grava a leitura no MySQL e recalcula "
           "o risco. Quando o risco muda, registra um alerta. A API Flask entrega ao painel web o risco de cada ponto, a "
           "previsão da Open-Meteo, o mapa de abrigos e o histórico. A regra é transparente: nível ≥ crítico → "
           "<font color='#dc2626'><b>PERIGO</b></font>; nível ≥ alerta → <font color='#d97706'><b>ATENÇÃO</b></font> "
           "(vira PERIGO com ≥ 10 mm de chuva prevista em 6 h); nível ≥ 70% do alerta com ≥ 25 mm em 6 h → ATENÇÃO; "
           "caso contrário → <font color='#16a34a'><b>NORMAL</b></font>. A tela de Gestão permite à Defesa Civil fazer "
           "o CRUD de sensores e abrigos com chave de operador."))

# 4. Arquitetura
s.append(P("4. Arquitetura e tecnologias", h2))
s.append(diagrama())
s.append(Spacer(1, 3))
s.append(tabela([
    ["Requisito", "Implementação"],
    ["API REST Flask (GET/POST/PUT/DELETE)", "<font name='Mono'>/api/sensores</font> e <font name='Mono'>/api/abrigos</font> "
     "com 200, 201 (+Location), 204, 400, 401, 404, 405, 409, 413, 415, 429 e 503; também /resumo, /clima, /alertas e /leituras"],
    ["MySQL sem ORM", "mysql-connector-python com pool; SQL puro e parametrizado na camada Model (<i>models/</i>)"],
    ["Fonte externa (requests + JSON)", "Open-Meteo: temperatura, umidade, chuva/hora e probabilidade; timeout 6 s, cache 10 min"],
    ["Interface web", "HTML/CSS/JS puro + Leaflet (mapa OSM), Chart.js (gráficos), Lucide (ícones), Plus Jakarta Sans"],
    ["Log em arquivo", "<i>logs/alerta_rio.log</i>: data e hora · origem · ação · resultado · detalhe (rotação a cada 1 MB)"],
    ["Módulo escolhido: sockets", "UDP (leve para dispositivos de campo) com ACK, limite de 1 KB e tolerância a pacotes ruins"],
    ["Organização: padrão <b>MVC</b>", "<b>Model</b> (<i>models/</i>): SQL, Open-Meteo e regra de risco, sem Flask. "
     "<b>View</b> (<i>views/</i>): HTML/CSS/JS e respostas JSON padronizadas. <b>Controller</b> (<i>controllers/</i>): "
     "um Blueprint por recurso, além do controller do pacote UDP e o de erros. <i>core/</i>: validação, segurança e log. "
     "Exceções próprias (ErroBanco, ErroValidacao, ClimaIndisponivel)"],
], [4.6 * cm, LW - 4.6 * cm]))

# 5. Modelo de dados
s.append(P("5. Modelo de dados", h2))
s.append(tabela([
    ["Tabela", "Campos", "Regras"],
    ["sensores", "id, codigo, nome, bairro, latitude, longitude, nivel_alerta_cm, nivel_critico_cm, ativo, criado_em, atualizado_em",
     "codigo UNIQUE; CHECK crítico &gt; alerta"],
    ["leituras", "id, sensor_id (FK), nivel_cm, registrado_em", "índice (sensor_id, data); ON DELETE CASCADE"],
    ["alertas", "id, sensor_id (FK), nivel_risco ENUM(normal, atencao, perigo), nivel_cm, mensagem, criado_em",
     "gravado só quando o risco muda"],
    ["abrigos", "id, nome, endereco, bairro, latitude, longitude, capacidade, ocupacao, aceita_pets, acessivel, ativo",
     "CHECK ocupação ≤ capacidade"],
], [2.2 * cm, 10.2 * cm, LW - 12.4 * cm], cor=colors.HexColor("#6d28d9")))
s.append(P("Relacionamentos: sensores 1:N leituras e sensores 1:N alertas. <b>LGPD:</b> não existe tabela de pessoas; "
           "o sistema funciona sem identificar o morador.", ParagraphStyle("x", parent=corpo, spaceBefore=3)))

# Imagem do painel
img = Image(IMG, width=LW * 0.80, height=LW * 0.80 * 900 / 1440)
s.append(KeepTogether([Spacer(1, 4), img, P("Figura 1: painel web em cenário de enchente simulada "
                                            "(dados fictícios, mapa © OpenStreetMap).", legenda)]))

# 6. Segurança
s.append(P("6. Segurança e privacidade", h2))
s.append(P("<b>Controles obrigatórios:</b> credenciais e segredos no <i>.env</i> (fora do Git, com <i>.env.example</i>); "
           "100% das consultas com parâmetros <font name='Mono'>%s</font>; validação de toda entrada (tipo, tamanho, regex, "
           "faixa geográfica do Brasil, regras de negócio e recusa de campos desconhecidos contra <i>mass assignment</i>); "
           "erros genéricos ao cliente com detalhe técnico só no log; coleta mínima: nenhum dado pessoal, e o log não guarda "
           "IP nem chaves. <b>Extras:</b> usuário de banco com privilégio mínimo (só SELECT, INSERT, UPDATE e DELETE), "
           "cabeçalhos CSP, X-Frame-Options e nosniff, corpo máximo de 16 KB e front-end que só usa <i>textContent</i>."))
s.append(tabela([
    ["Ameaça", "Impacto", "Mitigação implementada"],
    ["<b>1. Falsificação de leituras do sensor</b> (spoofing/replay via UDP)",
     "Alarme falso que gera pânico ou, pior, uma enchente real escondida",
     "Assinatura HMAC-SHA256 com segredo do .env e comparação em tempo constante; janela de 30 s e memória de assinaturas "
     "(anti-replay); sensor precisa estar cadastrado e ativo; validação e limite de 1 KB por pacote"],
    ["<b>2. Alteração não autorizada de dados</b> (força bruta na API de escrita)",
     "Abrigo apagado ou com vagas falsas, sensor desativado",
     "Chave de operador (X-API-Key) com <i>hmac.compare_digest</i>; rate limit de 30 escritas/min e 10 tentativas/min "
     "de login; tentativa negada registrada no log; chave guardada só no sessionStorage"],
    ["<b>3. Injeção</b> (SQL Injection e XSS armazenado)",
     "Vazamento ou destruição do banco; script malicioso no navegador do morador",
     "Queries parametrizadas; regex que bloqueia &lt; &gt; ; { }; usuário do banco sem DROP/ALTER; DOM montado com "
     "textContent; Content-Security-Policy <i>script-src 'self'</i>"],
], [4.2 * cm, 3.9 * cm, LW - 8.1 * cm], cor=VERM))

# 7. Validação
s.append(P("7. Validação e viabilidade", h2))
s.append(P("<b>Testes automatizados (pytest): 37 aprovados</b>, cobrindo a separação MVC (models sem Flask, controllers sem SQL), códigos HTTP, autenticação, cabeçalhos de segurança, "
           "entradas maliciosas (XSS, SQLi, coordenadas fora do Brasil, booleano disfarçado de número), regra de risco, "
           "HMAC e anti-replay. <b>Teste ponta a ponta:</b> CRUD real no MySQL com todos os status esperados; cenário "
           "<i>enchente</i> gerou alertas de ATENÇÃO e PERIGO em tempo real; o modo <i>--invasor</i> teve o pacote com "
           "assinatura falsa recusado (\"não autorizado\") e o reenvio de um pacote legítimo recusado (\"pacote expirado\"); "
           "a Open-Meteo respondeu ao vivo e, se cair, a API devolve 503 sem quebrar o painel. <b>Viabilidade:</b> "
           "Python, MySQL, Open-Meteo e OpenStreetMap são gratuitos. Cada ponto real exigiria um microcontrolador com "
           "sensor ultrassônico à prova d'água e alimentação solar, um hardware de baixo custo que pode ser mantido pela "
           "própria comunidade (o valor exato depende de cotação). A API roda num servidor pequeno."))

# 8. Limitações
s.append(P("8. Limitações e próximos passos", h2))
s.append(P("Sensores simulados; limiares fictícios (no mundo real viriam das cotas históricas da Defesa Civil e da ANA); "
           "sem notificação ativa (próximo passo: SMS ou WhatsApp com opt-in e o mínimo de dados); chave de operador única "
           "(ideal: login individual com perfis); execução local em HTTP (produção: HTTPS, Redis para o rate limit, backup "
           "do banco); não há validação com moradores reais, que seria o próximo passo antes de um piloto."))

# 9. Bônus
s.append(KeepTogether([P("9. Recursos além do conteúdo (bônus) e por que foram usados", h2), tabela([
    ["Recurso", "Justificativa"],
    ["HMAC-SHA256 + anti-replay", "UDP não autentica a origem. Sem assinatura, qualquer um na rede forjaria o nível do rio"],
    ["Flask-Limiter (rate limiting)", "Freia força bruta na chave de operador e o abuso da API"],
    ["CSP e cabeçalhos de segurança", "Segunda camada contra XSS e clickjacking, além da validação"],
    ["Pool de conexões MySQL", "API e servidor UDP acessam o banco ao mesmo tempo sem abrir conexão a cada requisição"],
    ["Leaflet/OSM, Chart.js, Lucide e Rich", "Mapa e gráfico tornam o risco compreensível num relance; Rich deixa a demo do socket legível"],
    ["pytest com monkeypatch", "Comprova segurança e regras sem depender do banco: qualquer avaliador consegue rodar"],
], [5 * cm, LW - 5 * cm], cor=colors.HexColor("#047857"))]))
s.append(Spacer(1, 5))
s.append(P("<b>Referências:</b> Defesa Civil RS, boletim de 03/06/2024 (estado.rs.gov.br); ONU Brasil, Objetivos de "
           "Desenvolvimento Sustentável (brasil.un.org/pt-br/sdgs); Open-Meteo Weather API (open-meteo.com); OpenStreetMap "
           "(openstreetmap.org); Lei 13.709/2018 (LGPD). Todos os sensores, abrigos e leituras do protótipo são fictícios.", ref))

doc.build(s, onFirstPage=rodape, onLaterPages=rodape)
print("ok")
