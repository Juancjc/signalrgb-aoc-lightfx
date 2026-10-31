<div align="center">

# signalrgb-aoc-lightfx

🟥🟧🟨🟩🟦🟪

**Plugin do SignalRGB para a iluminação RGB traseira dos monitores AOC AGON, sem o G-Menu.**

<sub>Projeto independente, compatível com monitores AOC. Não é um produto da AOC.</sub>

[![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-0078D6?logo=windows&logoColor=white)](#instalação)
[![NVIDIA](https://img.shields.io/badge/GPU-NVIDIA-76B900?logo=nvidia&logoColor=white)](#limitações)
[![SignalRGB](https://img.shields.io/badge/SignalRGB-plugin-8A2BE2)](https://signalrgb.com)
[![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white)](#rodar-direto-do-código)
[![Licença MIT](https://img.shields.io/badge/licen%C3%A7a-MIT-blue)](LICENSE)

[Início rápido](#início-rápido) •
[Instalação](#instalação) •
[Efeitos](#efeitos-do-monitor) •
[Protocolo](#protocolo) •
[Limitações](#limitações)

</div>

---

O **signalrgb-aoc-lightfx** é um plugin do [SignalRGB](https://signalrgb.com) que controla o **Light FX**, a iluminação RGB traseira dos monitores **AOC AGON**.

Testado no **AOC AG323FWG3R3** com placa **NVIDIA** (RTX 3070 Ti). Outros monitores AOC com Light FX usam o mesmo protocolo e devem funcionar. Se você testar outro modelo, abra uma issue contando o resultado.

> 🇺🇸 **English:** signalrgb-aoc-lightfx is an unofficial SignalRGB plugin for the Light FX RGB lighting on AOC AGON monitors. It talks DDC/CI through NVIDIA's NVAPI I2C via a small local Python bridge. See [Protocolo](#protocolo) for the reverse-engineered commands and the timing the monitor needs.

## Início rápido

1. Ligue o **DDC/CI** no menu do monitor.
2. Instale o `AOC-LightFX-Setup-x.y.z.exe`.
3. Abra o SignalRGB. O dispositivo **AOC Light FX** aparece sozinho.
4. Escolha um efeito colorido no SignalRGB, como o **Rainbow**.

Com o efeito padrão do monitor (**Motion Point**), um ponto gira pelo anel com as cores do SignalRGB, parecido com uma fan RGB.

## Como funciona

O Light FX não é controlado por USB. Ele usa o **DDC/CI**, o mesmo canal que o cabo de vídeo usa para ajustar brilho e contraste. O comando é uma extensão própria da AOC/TPV, que a API padrão do Windows não consegue enviar. Por isso o projeto tem duas partes:

```
SignalRGB ──UDP 127.0.0.1:21330──▶ ponte (Python) ──NVAPI I2C (DDC/CI)──▶ monitor
 (AOC_LightFX.js)
```

| Arquivo | Função |
|---|---|
| `AOC_LightFX.js` | Plugin do SignalRGB. Lê 8 pontos em anel no canvas, escolhe duas cores e envia para a ponte junto com o efeito do monitor |
| `aoc_lightfx_bridge.py` | Ponte. Recebe as cores e grava no monitor só os canais que mudaram. Também relê o monitor e corrige escritas perdidas |
| `aoc_lightfx.py` | Biblioteca DDC (NVAPI via `ctypes`, sem dependências externas) |
| `aoc_lightfx_tray.py` | Ícone na bandeja do Windows. Roda a ponte e tem o menu de opções |

## Instalação

**Requisitos:** Windows 10 ou 11 (64 bits), placa de vídeo **NVIDIA**, DDC/CI ligado no monitor e SignalRGB.

1. Baixe o `AOC-LightFX-Setup-x.y.z.exe` e rode. Ele não pede administrador e não precisa de Python.
2. O instalador coloca o plugin em `Documentos\WhirlwindFX\Plugins`, cria o atalho no Menu Iniciar e, se a opção estiver marcada, faz a ponte abrir junto com o Windows.
3. Reinicie o SignalRGB. O dispositivo **AOC Light FX** deve aparecer.

Para desinstalar, use **Configurações > Aplicativos** ou o atalho **Desinstalar AOC Light FX** no Menu Iniciar.

### Rodar direto do código

Requer **Python 3.8+** no PATH.

1. Copie `AOC_LightFX.js` para `Documentos\WhirlwindFX\Plugins`.
2. Rode `iniciar_ponte.bat`.
3. Opcional: rode `instalar_inicializacao.bat` para a ponte abrir junto com o Windows.

Para testar sem o SignalRGB (deixa o Light FX vermelho fixo):

```
python aoc_lightfx.py 255 0 0
```

### Gerar o instalador

Requer Python e [Inno Setup 6](https://jrsoftware.org/isinfo.php) (`winget install JRSoftware.InnoSetup`).

```
instalador\build.bat
```

O script empacota a ponte com o PyInstaller e gera o instalador em `instalador\Output`. Para lançar uma versão nova, altere `AppVersion` em `instalador\AOC_LightFX.iss`.

## Opções no SignalRGB

| Opção | Descrição |
|---|---|
| Modo de iluminação | `Canvas` segue o efeito do SignalRGB; `Forced` usa uma cor fixa |
| Cor forçada | Cor usada no modo `Forced` |
| Cor ao desligar | Cor enviada quando o SignalRGB fecha |
| Efeito do monitor | Animação feita pelo próprio monitor com as duas cores. Padrão: **Motion Point** |
| Escolha das cores | `Mais contrastantes`: as duas cores mais diferentes entre os 8 pontos. `Esquerda / direita`: média de cada metade do anel. `Média (cor única)`: uma cor só |
| Troca de cor nos efeitos animados | De quanto em quanto tempo as cores mudam num efeito animado: rápida, 1 s, 3 s (padrão) ou 6 s |
| Intensidade do Light FX | Baixo, Médio ou Forte |

## Efeitos do monitor

O monitor não aceita cor por LED. Ele recebe só duas cores, **frente** e **fundo**, e anima as duas com um efeito interno. O plugin escolhe essas duas cores a partir do canvas do SignalRGB.

Comportamento de cada efeito, gravado com webcam no AG323FWG3R3 (frente vermelha, fundo azul):

| Efeito | O que aparece no anel |
|---|---|
| **Motion Point** | Um ponto da cor da frente gira pelo anel sobre o fundo. É o que mais lembra uma fan RGB |
| **1 Way Filling** | A cor da frente vai enchendo o anel em uma direção |
| Simple Filling | Enche com a frente e volta para o fundo |
| Simple Shift, Gradient Shift, Water Wave | Ondas de brilho usando quase só a cor de fundo |
| Breathing, Flashing | O anel inteiro pulsa ou pisca |
| Zoom | Mistura frente e fundo pelo anel |
| Discolor | Ignora as cores personalizadas |
| Estático | Mostra só a cor de **fundo** |

> **Dica:** o monitor reinicia a animação sempre que a cor muda. Por isso, nos efeitos animados, o plugin só troca as cores a cada 3 s. Se quiser que acompanhe mais rápido, mude **Troca de cor nos efeitos animados**. Com `Rápida` a animação pode piscar.

Os efeitos da lista são os do AG323FWG3R3. Monitores com a lista nova de efeitos (Wave, Drip Fill etc.) recebem o equivalente mais próximo.

## Ícone na bandeja

O ícone mostra a cor que está sendo enviada ao monitor e fica cinza enquanto o SignalRGB não manda cores. Clique nele para abrir o menu:

| Opção | Descrição |
|---|---|
| Iniciar com o Windows | Liga ou desliga a abertura da ponte junto com o Windows |
| Fechar o G-Menu automaticamente | Fecha o G-Menu sempre que ele abrir, porque ele disputa o monitor com a ponte. Vem ligado |
| Fechar o G-Menu agora | Fecha o G-Menu uma vez |
| Abrir log | Abre o `ponte.log` |
| Sair | Encerra a ponte |

A opção do G-Menu fica salva em `config.json`. Para usar o G-Menu de novo, desmarque a opção ou saia da ponte.

## Limitações

- **Duas cores:** não dá para controlar LED por LED nem mostrar mais de duas cores ao mesmo tempo.
- **Velocidade:** o DDC do monitor é lento (veja [Tempos](#tempos)). Uma troca completa das duas cores leva cerca de 0,7 s, então efeitos rápidos ficam suavizados.
- **Só NVIDIA por enquanto.** AMD (ADL) e Intel (IGCL) também têm acesso I2C; contribuições são bem-vindas.
- **G-Menu:** usa o mesmo barramento e disputa com a ponte. Por padrão o ícone da bandeja fecha o G-Menu sozinho. Se ele estiver rodando como administrador, feche-o manualmente.
- **Monitor ou PC reiniciando:** desligar e ligar o monitor ou acordar o PC da suspensão ainda não foi testado. Se as luzes não voltarem, reinicie a ponte.

Problemas ficam registrados em `ponte.log`, na pasta da ponte.

## Protocolo

Os comandos foram identificados analisando o G-Menu (AOC) e confirmados no AG323FWG3R3.

**Escrita** (endereço I2C `0x37`, byte de destino `0x6E`):

```
51 86 03 F8 E1 <código> <valor_hi> <valor_lo> <checksum>
checksum = 0x6E XOR todos os bytes anteriores
```

**Leitura:** envie `51 84 01 F8 E1 <código> <checksum>` e leia do endereço `0x6F`. A resposta é:

```
6E 88 02 00 F8 <código> <max_hi> <max_lo> <atual_hi> <atual_lo> <checksum>
```

| Código | Função | Valores |
|---|---|---|
| `0x60` | Light FX (intensidade) | 0 desligado, 1 baixo, 2 médio, 3 forte |
| `0x61` | Modo (efeito) | Índice numa lista que depende do máximo informado pelo monitor (veja abaixo) |
| `0x62` | Pattern | 0 vermelho, 1 verde, 2 azul, 3 arco-íris, 4 personalizado |
| `0x63`–`0x65` | Cor da frente R/G/B | 0 até o máximo (100 no AG323FWG3R3) |
| `0x66`–`0x68` | Cor do fundo R/G/B | 0 até o máximo |

A lista de modos depende do máximo do código `0x61` (enums `LightFXMode_C/D/E/F/10` do G-Menu):

| Máximo | Lista |
|---|---|
| 12 | Static, SimpleShift, GradientShift, SimpleFilling, 1WayFilling, 2WayFilling, Breathing, MotionPoint, Zoom, Discolor, WaterWave, Flashing, Demo |
| 13 | Audio + a lista do 12 |
| 14 | Audio1, Audio2, Static, DarkPointSweep, GradientShift, Spread_Fill, DripFill, SpreadingDripFill, Breathing, LightPointSweep, Zoom, Rainbow, Wave, Flashing, Demo |
| 15 | LOL + a lista do 14 |
| 16 | CS + a lista do 14 |

### Tempos

O monitor **descarta escritas sem avisar**: a NVAPI responde sucesso mesmo quando o comando foi ignorado. Medido no AG323FWG3R3:

| Situação | Resultado |
|---|---|
| Escritas a 30–100 ms uma da outra | Uma sim, outra não, é perdida |
| Escritas a 110 ms ou mais | Nenhuma perdida |
| Depois de gravar `0x60`, `0x61` ou `0x62` | Monitor fica ~0,3 s ocupado |
| Leitura | ~50 ms entre o pedido e a resposta |

Por isso a ponte:

- espera **120 ms** entre qualquer acesso ao barramento (leitura ou escrita) e **0,4 s** depois de trocar intensidade, efeito ou pattern;
- confere `0x60`, `0x61` e `0x62` lendo de volta e grava de novo se não pegou;
- grava a cor de fundo antes da cor de frente, porque é o fundo que aparece no Estático;
- relê um canal de cor por segundo no Estático e regrava o que tiver se perdido.

## Aviso

Este é um projeto independente e **não oficial**, sem relação com AOC, TPV ou WhirlwindFX. Use por sua conta e risco. Os comandos são os mesmos que o G-Menu envia ao monitor.

AOC, AGON e Light FX são marcas da TPV Technology. SignalRGB é marca da WhirlwindFX. Elas são citadas só para indicar compatibilidade.

## Licença

[MIT](LICENSE)
