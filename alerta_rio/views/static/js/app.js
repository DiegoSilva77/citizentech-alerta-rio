/* ==========================================================================
   Alerta Rio · lógica do painel
   --------------------------------------------------------------------------
   Este arquivo só conversa com a NOSSA API (/api/...). Ele busca os dados,
   desenha cards, mapa e gráficos e atualiza tudo sozinho a cada 8 segundos.

   Regra de segurança importante: qualquer texto que vem da API entra na tela
   via textContent (nunca innerHTML). Assim, mesmo que alguém consiga gravar
   um "<script>" no nome de um abrigo, ele aparece como texto e não executa.
   ========================================================================== */

(() => {
  "use strict";

  const corpo = document.body;
  const CONFIG = {
    lat: Number(corpo.dataset.lat),
    lon: Number(corpo.dataset.lon),
    intervaloMs: 8000,          // painel
    intervaloClimaMs: 300000,   // previsão do tempo (5 min)
  };

  const RISCOS = ["normal", "atencao", "perigo"];
  const SITUACAO = {
    normal:  { titulo: "Tudo tranquilo",       icone: "shield-check",
               texto: "Nenhum rio acima do nível de alerta. Continue acompanhando." },
    atencao: { titulo: "Atenção",              icone: "triangle-alert",
               texto: "Há rios acima do nível de alerta. Separe documentos, remédios e carregue o celular." },
    perigo:  { titulo: "Perigo de enchente",   icone: "siren",
               texto: "Rio em nível crítico! Siga para o abrigo mais próximo e, se precisar, ligue 199." },
  };
  const ICONE_ALERTA = { normal: "circle-check", atencao: "triangle-alert", perigo: "siren" };
  const ROTULO_RISCO = { normal: "Normal", atencao: "Atenção", perigo: "Perigo" };
  const TENDENCIA = {
    subindo:  { icone: "trending-up",   texto: "subindo" },
    descendo: { icone: "trending-down", texto: "baixando" },
    estavel:  { icone: "minus",         texto: "estável" },
  };

  const estado = {
    sensores: [],
    abrigos: [],
    sensorSelecionado: null,
    ultimaAtualizacao: null,
    chave: lerChave(),
    graficoNivel: null,
    graficoChuva: null,
    mapa: null,
    marcadoresSensores: new Map(),
    marcadoresAbrigos: new Map(),
    mapaEnquadrado: false,
  };

  /* ------------------------------------------------------------------------
     Utilidades
     ------------------------------------------------------------------------ */

  /** Cria um elemento de forma segura. `texto` sempre vira textContent. */
  function el(tag, { classe, texto, atributos } = {}, ...filhos) {
    const no = document.createElement(tag);
    if (classe) no.className = classe;
    if (texto !== undefined && texto !== null) no.textContent = String(texto);
    if (atributos) Object.entries(atributos).forEach(([k, v]) => no.setAttribute(k, v));
    filhos.flat().filter(Boolean).forEach((f) => no.append(f));
    return no;
  }

  /** Placeholder de ícone do Lucide (vira <svg> quando chamamos desenharIcones). */
  function icone(nome) {
    const i = document.createElement("i");
    i.dataset.lucide = nome;
    return i;
  }

  function desenharIcones() {
    if (window.lucide) window.lucide.createIcons();
  }

  const riscoSeguro = (r) => (RISCOS.includes(r) ? r : "normal");

  function tempoRelativo(iso) {
    if (!iso) return "sem leitura";
    const segundos = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
    if (segundos < 60) return `há ${segundos}s`;
    if (segundos < 3600) return `há ${Math.floor(segundos / 60)} min`;
    if (segundos < 86400) return `há ${Math.floor(segundos / 3600)} h`;
    return new Date(iso).toLocaleDateString("pt-BR");
  }

  const horaCurta = (iso) =>
    new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });

  function toast(mensagem, tipo = "info") {
    const icones = { info: "info", sucesso: "circle-check", erro: "circle-alert" };
    const t = el("div", { classe: `toast toast--${tipo}` }, icone(icones[tipo]), el("span", { texto: mensagem }));
    document.getElementById("toasts").append(t);
    desenharIcones();
    setTimeout(() => t.remove(), 4500);
  }

  // A chave fica no sessionStorage: some sozinha quando a aba é fechada.
  function lerChave() {
    try { return sessionStorage.getItem("alertaRioChave") || ""; } catch { return ""; }
  }
  function salvarChave(valor) {
    estado.chave = valor;
    try {
      if (valor) sessionStorage.setItem("alertaRioChave", valor);
      else sessionStorage.removeItem("alertaRioChave");
    } catch { /* navegador em modo privado: segue só em memória */ }
  }

  /** Chamada à nossa API, já tratando JSON, chave de operador e erros. */
  async function api(caminho, { metodo = "GET", corpo, autenticado = false } = {}) {
    const cabecalhos = { Accept: "application/json" };
    if (corpo !== undefined) cabecalhos["Content-Type"] = "application/json";
    if (autenticado) cabecalhos["X-API-Key"] = estado.chave;

    const resposta = await fetch(caminho, {
      method: metodo,
      headers: cabecalhos,
      body: corpo !== undefined ? JSON.stringify(corpo) : undefined,
    });
    if (resposta.status === 204) return null;

    let dados = null;
    try { dados = await resposta.json(); } catch { /* resposta sem corpo */ }

    if (!resposta.ok) {
      const erro = new Error((dados && dados.erro) || "Não foi possível falar com o servidor.");
      erro.status = resposta.status;
      erro.campos = dados && dados.campos;
      throw erro;
    }
    return dados;
  }

  /* ------------------------------------------------------------------------
     Situação geral e indicadores
     ------------------------------------------------------------------------ */

  function renderSituacao(resumo) {
    const risco = riscoSeguro(resumo.risco_geral);
    const info = SITUACAO[risco];
    const caixa = document.getElementById("situacao");
    caixa.className = `situacao situacao--${risco}`;
    document.getElementById("situacao-titulo").textContent = info.titulo;
    document.getElementById("situacao-texto").textContent = info.texto;
    caixa.querySelector(".situacao__icone").replaceChildren(icone(info.icone));
  }

  function renderIndicadores(resumo) {
    const t = resumo.totais;
    document.getElementById("total-sensores").textContent = t.sensores_ativos;
    document.getElementById("total-atencao").textContent = t.em_atencao;
    document.getElementById("total-perigo").textContent = t.em_perigo;
    document.getElementById("total-vagas").textContent = t.vagas_livres.toLocaleString("pt-BR");
    document.getElementById("total-abrigos").textContent = t.abrigos;
  }

  /* ------------------------------------------------------------------------
     Cards de sensores
     ------------------------------------------------------------------------ */

  function cartaoSensor(s) {
    const risco = riscoSeguro(s.risco);
    const nivel = s.ultimo_nivel_cm;
    // A régua vai até 120% do nível crítico, para sobrar espaço visual
    const escala = s.nivel_critico_cm * 1.2;
    const pctAgua = nivel ? Math.min(100, (nivel / escala) * 100) : 0;
    const pctAlerta = (s.nivel_alerta_cm / escala) * 100;
    const pctCritico = (s.nivel_critico_cm / escala) * 100;
    const tend = TENDENCIA[s.tendencia] || TENDENCIA.estavel;

    const marcaAlerta = el("span", { classe: "regua__marca", atributos: { title: `Alerta: ${s.nivel_alerta_cm} cm` } });
    marcaAlerta.style.left = `${pctAlerta}%`;
    const marcaCritico = el("span", { classe: "regua__marca", atributos: { title: `Crítico: ${s.nivel_critico_cm} cm` } });
    marcaCritico.style.left = `${pctCritico}%`;
    marcaCritico.style.background = "var(--perigo)";
    const agua = el("div", { classe: "regua__agua" });
    agua.style.width = `${pctAgua}%`;

    const botao = el("button", {
      classe: `sensor sensor--${risco}${estado.sensorSelecionado === s.id ? " sensor--selecionado" : ""}`,
      atributos: { type: "button", "aria-label": `Ver gráfico de ${s.nome}` },
    },
      el("div", { classe: "sensor__topo" },
        el("span", { classe: "sensor__codigo", texto: s.codigo }),
        el("span", { classe: `selo selo--${risco}` }, icone(ICONE_ALERTA[risco]), ROTULO_RISCO[risco])),
      el("div", {},
        el("p", { classe: "sensor__nome", texto: s.nome }),
        el("p", { classe: "sensor__bairro" }, icone("map-pin"), s.bairro)),
      el("div", { classe: "sensor__nivel" },
        el("strong", { texto: nivel != null ? nivel.toFixed(0) : "--" }),
        el("span", { texto: "cm" }),
        el("span", { classe: `sensor__tendencia tendencia--${s.tendencia}` }, icone(tend.icone), tend.texto)),
      el("div", { classe: "regua" }, agua, marcaAlerta, marcaCritico),
      el("div", { classe: "sensor__rodape" },
        el("span", { texto: `alerta ${s.nivel_alerta_cm} · crítico ${s.nivel_critico_cm}` }),
        el("span", { texto: tempoRelativo(s.ultima_leitura_em) })),
    );
    botao.addEventListener("click", () => selecionarSensor(s.id, true));
    return botao;
  }

  function renderSensores(sensores) {
    const lista = document.getElementById("lista-sensores");
    if (!sensores.length) {
      lista.replaceChildren(el("p", { classe: "vazio", texto: "Nenhum sensor ativo cadastrado." }));
      return;
    }
    lista.replaceChildren(...sensores.map(cartaoSensor));
  }

  /* ------------------------------------------------------------------------
     Mapa (Leaflet + tiles CARTO/OpenStreetMap)
     ------------------------------------------------------------------------ */

  const SVG_CASA =
    '<span class="pino-abrigo"><svg viewBox="0 0 24 24"><path d="M3 10.5 12 3l9 7.5"/>' +
    '<path d="M5 9.5V21h14V9.5"/><path d="M10 21v-6h4v6"/></svg></span>';

  function iniciarMapa() {
    if (!window.L) return;
    estado.mapa = L.map("mapa", { scrollWheelZoom: false }).setView([CONFIG.lat, CONFIG.lon], 12);
    // Mapa base aberto do OpenStreetMap (gratuito, mantido pela comunidade)
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(estado.mapa);
  }

  function popupSensor(s) {
    const risco = riscoSeguro(s.risco);
    return el("div", {},
      el("p", { classe: "popup__titulo", texto: s.nome }),
      el("p", { classe: "popup__linha", texto: `${s.codigo} · ${s.bairro}` }),
      el("p", { classe: "popup__linha", texto: `Nível: ${s.ultimo_nivel_cm ?? "--"} cm (crítico ${s.nivel_critico_cm} cm)` }),
      el("span", { classe: `selo selo--${risco}`, texto: ROTULO_RISCO[risco] }));
  }

  function popupAbrigo(a) {
    const livres = a.capacidade - a.ocupacao;
    return el("div", {},
      el("p", { classe: "popup__titulo", texto: a.nome }),
      el("p", { classe: "popup__linha", texto: a.endereco }),
      el("p", { classe: "popup__linha", texto: `${livres} vagas livres de ${a.capacidade}` }),
      el("p", { classe: "popup__linha", texto: [a.aceita_pets && "aceita animais", a.acessivel && "acessível"].filter(Boolean).join(" · ") }));
  }

  /** Atualiza os marcadores sem recriar o mapa (assim o popup aberto não fecha). */
  function sincronizarMarcadores(colecao, itens, criarIcone, criarPopup, aoClicar) {
    const idsAtuais = new Set(itens.map((i) => i.id));
    for (const [id, marcador] of colecao) {
      if (!idsAtuais.has(id)) { marcador.remove(); colecao.delete(id); }
    }
    for (const item of itens) {
      let marcador = colecao.get(item.id);
      if (!marcador) {
        marcador = L.marker([item.latitude, item.longitude], { icon: criarIcone(item) }).addTo(estado.mapa);
        marcador.bindPopup(criarPopup(item));
        if (aoClicar) marcador.on("click", () => aoClicar(item.id));
        colecao.set(item.id, marcador);
      } else {
        marcador.setLatLng([item.latitude, item.longitude]);
        marcador.setIcon(criarIcone(item));
        marcador.setPopupContent(criarPopup(item));
      }
    }
  }

  function atualizarMapa() {
    if (!estado.mapa) return;
    sincronizarMarcadores(
      estado.marcadoresSensores, estado.sensores,
      (s) => L.divIcon({ className: "", html: `<span class="pino pino--${riscoSeguro(s.risco)}"></span>`, iconSize: [22, 22], iconAnchor: [11, 11] }),
      popupSensor,
      (id) => selecionarSensor(id, false),
    );
    sincronizarMarcadores(
      estado.marcadoresAbrigos, estado.abrigos,
      () => L.divIcon({ className: "", html: SVG_CASA, iconSize: [30, 30], iconAnchor: [15, 15] }),
      popupAbrigo,
    );

    // Na primeira carga, enquadra o mapa para mostrar todos os pontos
    if (!estado.mapaEnquadrado && (estado.sensores.length || estado.abrigos.length)) {
      const pontos = [...estado.sensores, ...estado.abrigos].map((p) => [p.latitude, p.longitude]);
      estado.mapa.fitBounds(pontos, { padding: [30, 30] });
      estado.mapaEnquadrado = true;
    }
  }

  function mostrarNoMapa(abrigoId) {
    const marcador = estado.marcadoresAbrigos.get(abrigoId);
    if (!marcador) return;
    document.getElementById("mapa").scrollIntoView({ behavior: "smooth", block: "center" });
    estado.mapa.flyTo(marcador.getLatLng(), 15, { duration: 0.8 });
    setTimeout(() => marcador.openPopup(), 850);
  }

  /* ------------------------------------------------------------------------
     Linha do tempo de alertas
     ------------------------------------------------------------------------ */

  function renderAlertas(alertas) {
    const lista = document.getElementById("lista-alertas");
    if (!alertas.length) {
      lista.replaceChildren(el("li", { classe: "vazio", texto: "Nenhum alerta registrado." }));
      return;
    }
    lista.replaceChildren(...alertas.map((a) => {
      const risco = riscoSeguro(a.nivel_risco);
      return el("li", { classe: `alerta--${risco}` },
        el("span", { classe: "alerta__icone" }, icone(ICONE_ALERTA[risco])),
        el("div", {},
          el("p", { classe: "alerta__texto", texto: a.mensagem }),
          el("p", { classe: "alerta__meta", texto: `${a.sensor_codigo} · ${a.bairro} · ${tempoRelativo(a.criado_em)}` })));
    }));
  }

  /* ------------------------------------------------------------------------
     Abrigos
     ------------------------------------------------------------------------ */

  function renderAbrigos(abrigos) {
    const lista = document.getElementById("lista-abrigos");
    if (!abrigos.length) {
      lista.replaceChildren(el("p", { classe: "vazio", texto: "Nenhum abrigo ativo." }));
      return;
    }
    const ordenados = [...abrigos].sort((a, b) => (b.capacidade - b.ocupacao) - (a.capacidade - a.ocupacao));
    lista.replaceChildren(...ordenados.map((a) => {
      const livres = a.capacidade - a.ocupacao;
      const pct = Math.round((a.ocupacao / a.capacidade) * 100);
      const barra = el("div", { classe: `lotacao__barra${pct >= 90 ? " lotacao__barra--cheio" : ""}` });
      barra.style.width = `${pct}%`;

      const botaoMapa = el("button", { classe: "botao-link", atributos: { type: "button" } }, icone("navigation"), "Ver no mapa");
      botaoMapa.addEventListener("click", () => mostrarNoMapa(a.id));

      return el("article", { classe: "abrigo" },
        el("div", {},
          el("p", { classe: "abrigo__nome", texto: a.nome }),
          el("p", { classe: "abrigo__endereco" }, icone("map-pin"), `${a.endereco} · ${a.bairro}`)),
        el("div", { classe: "abrigo__vagas" },
          el("span", {}, el("strong", { texto: livres }), " vagas livres"),
          el("span", { texto: `${pct}% ocupado` })),
        el("div", { classe: "lotacao" }, barra),
        el("div", { classe: "abrigo__recursos" },
          el("span", { classe: `recurso${a.aceita_pets ? " recurso--sim" : ""}` }, icone("paw-print"), a.aceita_pets ? "Aceita animais" : "Sem animais"),
          el("span", { classe: `recurso${a.acessivel ? " recurso--sim" : ""}` }, icone("accessibility"), a.acessivel ? "Acessível" : "Sem acessibilidade")),
        botaoMapa);
    }));
  }

  /* ------------------------------------------------------------------------
     Gráficos (Chart.js)
     ------------------------------------------------------------------------ */

  if (window.Chart) {
    Chart.defaults.font.family = "'Plus Jakarta Sans', system-ui, sans-serif";
    Chart.defaults.color = "#5b6b80";
  }

  function degradeAgua(contexto) {
    const { ctx, chartArea } = contexto.chart;
    if (!chartArea) return "rgba(14,165,233,.2)";
    const g = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
    g.addColorStop(0, "rgba(14,165,233,.35)");
    g.addColorStop(1, "rgba(14,165,233,0)");
    return g;
  }

  function desenharGraficoNivel(sensor, leituras) {
    if (!window.Chart) return;
    document.getElementById("grafico-titulo").textContent = `Nível do rio · ${sensor.nome}`;
    const rotulos = leituras.map((l) => horaCurta(l.registrado_em));
    const niveis = leituras.map((l) => l.nivel_cm);
    const linha = (valor) => rotulos.map(() => valor);

    if (!estado.graficoNivel) {
      estado.graficoNivel = new Chart(document.getElementById("grafico-nivel"), {
        type: "line",
        data: {
          labels: rotulos,
          datasets: [
            { label: "Nível (cm)", data: niveis, borderColor: "#1d70b8", backgroundColor: degradeAgua,
              fill: true, tension: 0.35, pointRadius: 0, borderWidth: 2.5 },
            { label: "Alerta", data: linha(sensor.nivel_alerta_cm), borderColor: "#d97706",
              borderDash: [6, 6], pointRadius: 0, borderWidth: 1.5, fill: false },
            { label: "Crítico", data: linha(sensor.nivel_critico_cm), borderColor: "#dc2626",
              borderDash: [6, 6], pointRadius: 0, borderWidth: 1.5, fill: false },
          ],
        },
        options: {
          responsive: true, maintainAspectRatio: false, animation: { duration: 300 },
          interaction: { mode: "index", intersect: false },
          plugins: { legend: { labels: { usePointStyle: true, boxWidth: 8 } } },
          scales: {
            x: { grid: { display: false }, ticks: { maxTicksLimit: 6 } },
            y: { grid: { color: "#eef2f7" }, ticks: { callback: (v) => `${v} cm` } },
          },
        },
      });
      return;
    }
    const g = estado.graficoNivel;
    g.data.labels = rotulos;
    g.data.datasets[0].data = niveis;
    g.data.datasets[1].data = linha(sensor.nivel_alerta_cm);
    g.data.datasets[2].data = linha(sensor.nivel_critico_cm);
    g.update("none");
  }

  function desenharGraficoChuva(previsao) {
    if (!window.Chart) return;
    const rotulos = previsao.proximas_horas.map((h) => h.hora);
    const chuva = previsao.proximas_horas.map((h) => h.chuva_mm);
    const prob = previsao.proximas_horas.map((h) => h.probabilidade);

    if (estado.graficoChuva) {
      estado.graficoChuva.data.labels = rotulos;
      estado.graficoChuva.data.datasets[0].data = chuva;
      estado.graficoChuva.data.datasets[1].data = prob;
      estado.graficoChuva.update();
      return;
    }
    estado.graficoChuva = new Chart(document.getElementById("grafico-chuva"), {
      data: {
        labels: rotulos,
        datasets: [
          { type: "bar", label: "Chuva (mm)", data: chuva, backgroundColor: "#0ea5e9", borderRadius: 6, yAxisID: "y" },
          { type: "line", label: "Probabilidade (%)", data: prob, borderColor: "#94a3b8", pointRadius: 0,
            borderWidth: 2, tension: 0.35, yAxisID: "y1" },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: { legend: { labels: { usePointStyle: true, boxWidth: 8 } } },
        scales: {
          x: { grid: { display: false }, ticks: { maxTicksLimit: 8 } },
          y: { beginAtZero: true, suggestedMax: 5, grid: { color: "#eef2f7" }, ticks: { callback: (v) => `${v} mm` } },
          y1: { position: "right", min: 0, max: 100, grid: { display: false }, ticks: { callback: (v) => `${v}%` } },
        },
      },
    });
  }

  /* ------------------------------------------------------------------------
     Ciclo de atualização
     ------------------------------------------------------------------------ */

  async function selecionarSensor(id, rolar) {
    estado.sensorSelecionado = id;
    renderSensores(estado.sensores);
    desenharIcones();
    await atualizarGraficoNivel();
    if (rolar) document.getElementById("grafico-nivel").scrollIntoView({ behavior: "smooth", block: "center" });
  }

  async function atualizarGraficoNivel() {
    const sensor = estado.sensores.find((s) => s.id === estado.sensorSelecionado);
    if (!sensor) return;
    try {
      const leituras = await api(`/api/sensores/${sensor.id}/leituras?limite=40`);
      desenharGraficoNivel(sensor, leituras);
    } catch { /* o próximo ciclo tenta de novo */ }
  }

  /** Se nenhum sensor está selecionado, começamos pelo mais grave. */
  function escolherSensorInicial() {
    if (estado.sensores.some((s) => s.id === estado.sensorSelecionado)) return;
    const ordem = { perigo: 0, atencao: 1, normal: 2 };
    const maisGrave = [...estado.sensores].sort((a, b) => ordem[a.risco] - ordem[b.risco])[0];
    estado.sensorSelecionado = maisGrave ? maisGrave.id : null;
  }

  async function atualizarPainel() {
    try {
      const [resumo, alertas, abrigos] = await Promise.all([
        api("/api/resumo"),
        api("/api/alertas?limite=15"),
        api("/api/abrigos?ativos=1"),
      ]);
      estado.sensores = resumo.sensores;
      estado.abrigos = abrigos;
      escolherSensorInicial();

      renderSituacao(resumo);
      renderIndicadores(resumo);
      renderSensores(estado.sensores);
      renderAlertas(alertas);
      renderAbrigos(abrigos);
      atualizarMapa();
      desenharIcones();
      await atualizarGraficoNivel();

      estado.ultimaAtualizacao = Date.now();
      document.querySelector(".ao-vivo").classList.remove("ao-vivo--offline");
    } catch {
      document.querySelector(".ao-vivo").classList.add("ao-vivo--offline");
      document.getElementById("atualizado-ha").textContent = "sem conexão com o servidor";
    }
  }

  async function atualizarClima() {
    try {
      const previsao = await api("/api/clima");
      document.getElementById("clima-temp").textContent = previsao.atual.temperatura_c.toFixed(0);
      document.getElementById("clima-desc").textContent =
        `${previsao.atual.descricao} · umidade ${previsao.atual.umidade_pct}%`;
      document.getElementById("chuva-6h").textContent = previsao.chuva_6h_mm.toFixed(1);
      document.getElementById("chuva-24h").textContent = previsao.chuva_24h_mm.toFixed(1);
      // Troca o ícone conforme o tempo (sol, nuvem, chuva...)
      const caixa = document.querySelector(".indicador__icone--sol");
      caixa.replaceChildren(icone(previsao.atual.icone || "cloud"));
      desenharIcones();
      desenharGraficoChuva(previsao);
    } catch {
      document.getElementById("clima-desc").textContent = "Previsão indisponível no momento";
    }
  }

  function atualizarRelogio() {
    if (!estado.ultimaAtualizacao) return;
    const s = Math.round((Date.now() - estado.ultimaAtualizacao) / 1000);
    document.getElementById("atualizado-ha").textContent = s < 2 ? "agora mesmo" : `atualizado há ${s}s`;
  }

  /* ------------------------------------------------------------------------
     Abas
     ------------------------------------------------------------------------ */

  function trocarAba(nome) {
    document.querySelectorAll(".aba").forEach((b) => b.classList.toggle("aba--ativa", b.dataset.aba === nome));
    document.getElementById("aba-painel").hidden = nome !== "painel";
    document.getElementById("aba-gestao").hidden = nome !== "gestao";
    if (nome === "painel" && estado.mapa) setTimeout(() => estado.mapa.invalidateSize(), 50);
    if (nome === "gestao") carregarGestao();
  }

  /* ------------------------------------------------------------------------
     Gestão (CRUD com chave de operador)
     ------------------------------------------------------------------------ */

  function atualizarEstadoChave() {
    const logado = Boolean(estado.chave);
    document.getElementById("campo-chave").hidden = logado;
    document.querySelector("#form-chave [type=submit]").hidden = logado;
    document.getElementById("botao-sair").hidden = !logado;
  }

  function exigirChave() {
    if (estado.chave) return true;
    toast("Entre com a chave de operador primeiro.", "erro");
    document.getElementById("campo-chave").focus();
    return false;
  }

  /** Trata erros de escrita: 401 desloga, os outros mostram a mensagem da API. */
  function tratarErroEscrita(erro) {
    if (erro.status === 401) {
      salvarChave("");
      atualizarEstadoChave();
      toast("Chave de operador inválida. Entre novamente.", "erro");
    } else {
      toast(erro.message, "erro");
    }
  }

  function botaoAcao(nomeIcone, rotulo, aoClicar, perigo = false) {
    const b = el("button", { classe: `botao-icone${perigo ? " botao-icone--perigo" : ""}`, atributos: { type: "button", title: rotulo, "aria-label": rotulo } }, icone(nomeIcone));
    b.addEventListener("click", aoClicar);
    return b;
  }

  function linhaVazia(colunas, texto) {
    return el("tr", {}, el("td", { classe: "tabela__vazio", texto, atributos: { colspan: colunas } }));
  }

  async function carregarGestao() {
    atualizarEstadoChave();
    try {
      const [sensores, abrigos] = await Promise.all([api("/api/sensores"), api("/api/abrigos")]);

      const corpoSensores = document.getElementById("tabela-sensores");
      corpoSensores.replaceChildren(...(sensores.length ? sensores.map((s) => el("tr", {},
        el("td", {}, el("span", { classe: "sensor__codigo", texto: s.codigo })),
        el("td", { texto: s.nome }),
        el("td", { texto: s.bairro }),
        el("td", { texto: `${s.nivel_alerta_cm} cm` }),
        el("td", { texto: `${s.nivel_critico_cm} cm` }),
        el("td", {}, el("span", { classe: `selo selo--${s.ativo ? "ativo" : "inativo"}`, texto: s.ativo ? "Ativo" : "Inativo" })),
        el("td", {}, el("div", { classe: "tabela__acoes" },
          botaoAcao("pencil", "Editar", () => abrirModalSensor(s)),
          botaoAcao("trash-2", "Excluir", () => excluir("sensores", s.id, `o sensor ${s.codigo}`), true))),
      )) : [linhaVazia(7, "Nenhum sensor cadastrado.")]));

      const corpoAbrigos = document.getElementById("tabela-abrigos");
      corpoAbrigos.replaceChildren(...(abrigos.length ? abrigos.map((a) => el("tr", {},
        el("td", { texto: a.nome }),
        el("td", { texto: a.bairro }),
        el("td", { texto: `${a.ocupacao} / ${a.capacidade}` }),
        el("td", {}, el("div", { classe: "abrigo__recursos" },
          a.aceita_pets ? el("span", { classe: "recurso recurso--sim" }, icone("paw-print"), "Pets") : null,
          a.acessivel ? el("span", { classe: "recurso recurso--sim" }, icone("accessibility"), "PcD") : null)),
        el("td", {}, el("span", { classe: `selo selo--${a.ativo ? "ativo" : "inativo"}`, texto: a.ativo ? "Ativo" : "Inativo" })),
        el("td", {}, el("div", { classe: "tabela__acoes" },
          botaoAcao("pencil", "Editar", () => abrirModalAbrigo(a)),
          botaoAcao("trash-2", "Excluir", () => excluir("abrigos", a.id, `o abrigo "${a.nome}"`), true))),
      )) : [linhaVazia(6, "Nenhum abrigo cadastrado.")]));

      desenharIcones();
    } catch (erro) {
      toast(erro.message, "erro");
    }
  }

  async function excluir(recurso, id, descricao) {
    if (!exigirChave()) return;
    if (!window.confirm(`Tem certeza que deseja excluir ${descricao}? Essa ação não pode ser desfeita.`)) return;
    try {
      await api(`/api/${recurso}/${id}`, { metodo: "DELETE", autenticado: true });
      toast("Excluído com sucesso.", "sucesso");
      carregarGestao();
      atualizarPainel();
    } catch (erro) {
      tratarErroEscrita(erro);
    }
  }

  /* ---- Modais de formulário ---- */

  function preencherFormulario(form, dados) {
    form.reset();
    form.querySelectorAll("input").forEach((campo) => {
      campo.classList.remove("invalido");
      if (!(campo.name in dados)) return;
      if (campo.type === "checkbox") campo.checked = Boolean(dados[campo.name]);
      else campo.value = dados[campo.name];
    });
    form.querySelector("[data-erro]").hidden = true;
  }

  /** Lê o formulário convertendo cada campo para o tipo certo (número, booleano, texto). */
  function lerFormulario(form) {
    const dados = {};
    form.querySelectorAll("input[name]").forEach((campo) => {
      if (campo.type === "checkbox") dados[campo.name] = campo.checked;
      else if (campo.type === "number") dados[campo.name] = campo.value === "" ? null : Number(campo.value);
      else dados[campo.name] = campo.value.trim();
    });
    return dados;
  }

  function mostrarErrosFormulario(form, erro) {
    const caixa = form.querySelector("[data-erro]");
    form.querySelectorAll("input").forEach((c) => c.classList.remove("invalido"));
    let texto = erro.message;
    if (erro.campos) {
      texto = Object.entries(erro.campos).map(([campo, msg]) => {
        const input = form.querySelector(`[name="${CSS.escape(campo)}"]`);
        if (input) input.classList.add("invalido");
        return `• ${campo.replaceAll("_", " ")}: ${msg}`;
      }).join("\n");
    }
    caixa.textContent = texto;
    caixa.hidden = false;
  }

  let edicao = { recurso: null, id: null };

  function abrirModalSensor(sensor = null) {
    if (!exigirChave()) return;
    edicao = { recurso: "sensores", id: sensor ? sensor.id : null };
    document.getElementById("modal-sensor-titulo").textContent = sensor ? `Editar sensor ${sensor.codigo}` : "Novo sensor";
    preencherFormulario(document.getElementById("form-sensor"),
      sensor || { latitude: CONFIG.lat, longitude: CONFIG.lon, ativo: true });
    document.getElementById("modal-sensor").showModal();
  }

  function abrirModalAbrigo(abrigo = null) {
    if (!exigirChave()) return;
    edicao = { recurso: "abrigos", id: abrigo ? abrigo.id : null };
    document.getElementById("modal-abrigo-titulo").textContent = abrigo ? "Editar abrigo" : "Novo abrigo";
    preencherFormulario(document.getElementById("form-abrigo"),
      abrigo || { latitude: CONFIG.lat, longitude: CONFIG.lon, ocupacao: 0, ativo: true });
    document.getElementById("modal-abrigo").showModal();
  }

  async function salvarFormulario(evento) {
    evento.preventDefault();
    const form = evento.currentTarget;
    const dados = lerFormulario(form);
    if (dados.codigo) dados.codigo = dados.codigo.toUpperCase();

    const { recurso, id } = edicao;
    const botao = form.querySelector("[type=submit]");
    botao.disabled = true;
    try {
      await api(id ? `/api/${recurso}/${id}` : `/api/${recurso}`, {
        metodo: id ? "PUT" : "POST", corpo: dados, autenticado: true,
      });
      form.closest("dialog").close();
      toast(id ? "Alterações salvas." : "Cadastro criado com sucesso.", "sucesso");
      carregarGestao();
      atualizarPainel();
    } catch (erro) {
      if (erro.status === 401) { form.closest("dialog").close(); tratarErroEscrita(erro); }
      else mostrarErrosFormulario(form, erro);
    } finally {
      botao.disabled = false;
    }
  }

  /* ------------------------------------------------------------------------
     Eventos e inicialização
     ------------------------------------------------------------------------ */

  function ligarEventos() {
    document.querySelectorAll(".aba").forEach((b) => b.addEventListener("click", () => trocarAba(b.dataset.aba)));

    document.getElementById("form-chave").addEventListener("submit", async (e) => {
      e.preventDefault();
      const campo = document.getElementById("campo-chave");
      const chave = campo.value.trim();
      if (chave.length < 16) { toast("A chave tem pelo menos 16 caracteres.", "erro"); return; }
      salvarChave(chave);
      try {
        await api("/api/operador/verificar", { autenticado: true });
        campo.value = "";
        atualizarEstadoChave();
        toast("Acesso de operador liberado.", "sucesso");
      } catch (erro) {
        salvarChave("");
        toast(erro.status === 401 ? "Chave incorreta." : erro.message, "erro");
      }
    });

    document.getElementById("botao-sair").addEventListener("click", () => {
      salvarChave("");
      atualizarEstadoChave();
      toast("Você saiu do modo operador.");
    });

    document.getElementById("novo-sensor").addEventListener("click", () => abrirModalSensor());
    document.getElementById("novo-abrigo").addEventListener("click", () => abrirModalAbrigo());
    document.getElementById("form-sensor").addEventListener("submit", salvarFormulario);
    document.getElementById("form-abrigo").addEventListener("submit", salvarFormulario);
    document.querySelectorAll("[data-fechar]").forEach((b) =>
      b.addEventListener("click", () => b.closest("dialog").close()));
  }

  function iniciar() {
    desenharIcones();
    ligarEventos();
    iniciarMapa();
    atualizarPainel();
    atualizarClima();
    setInterval(atualizarPainel, CONFIG.intervaloMs);
    setInterval(atualizarClima, CONFIG.intervaloClimaMs);
    setInterval(atualizarRelogio, 1000);
  }

  iniciar();
})();
