# AOC Light FX para SignalRGB

Plugin do [SignalRGB](https://signalrgb.com) para controlar o **Light FX** (iluminação RGB traseira) dos monitores **AOC AGON** sem depender do G-Menu.

Testado no **AOC AG323FWG3R3** com placa **NVIDIA** (RTX 3070 Ti). Outros monitores AOC com Light FX usam o mesmo protocolo e devem funcionar. Se testar outro modelo, abra uma issue contando o resultado.

> 🇺🇸 **English:** SignalRGB plugin for the Light FX RGB lighting on AOC AGON monitors. It talks DDC/CI through NVIDIA's NVAPI I2C via a small local Python bridge. See [Protocol](#protocolo) for the reverse-engineered commands.

## Como funciona

O Light FX não é controlado por USB, e sim por **DDC/CI**, o mesmo canal que o cabo de vídeo usa para ajustar brilho e contraste. O comando é uma extensão própria da AOC/TPV que a API padrão do Windows não consegue enviar. Por isso existem duas partes:

```
SignalRGB ──UDP 127.0.0.1:21330──▶ aoc_lightfx_bridge.py ──NVAPI I2C (DDC/CI)──▶ monitor
 (AOC_LightFX.js)
```

- **`AOC_LightFX.js`**: o plugin do SignalRGB. Cria um dispositivo com 8 pontos em anel, escolhe duas cores do efeito e envia para a ponte junto com o efeito do monitor.
- **`aoc_lightfx_bridge.py`**: a ponte. Recebe as cores e grava no monitor só o que mudou, cerca de 10 atualizações por segundo. Ela também relê o monitor e corrige o que se perder.
- **`aoc_lightfx.py`**: a biblioteca DDC (NVAPI via `ctypes`, sem dependências externas).
- **`aoc_lightfx_tray.py`**: o ícone na bandeja do Windows. Roda a ponte e tem o menu de opções.

## Requisitos

- Windows 10 ou 11 (64 bits)
- Placa de vídeo **NVIDIA**
- DDC/CI **ligado** no menu do monitor
- SignalRGB

## Instalação

1. Baixe o `AOC-LightFX-Setup-x.y.z.exe` e rode. Ele não pede administrador e não precisa de Python.
2. O instalador coloca o plugin na pasta do SignalRGB (`Documentos\WhirlwindFX\Plugins`), cria o atalho no Menu Iniciar e, se a opção estiver marcada, faz a ponte abrir junto com o Windows.
3. Reinicie o SignalRGB. O dispositivo **AOC Light FX** deve aparecer.

Para desinstalar, use **Configurações > Aplicativos** ou o atalho **Desinstalar AOC Light FX** no Menu Iniciar.

### Rodar direto do código (sem instalar)

Requer **Python 3.8+** no PATH.

1. Copie `AOC_LightFX.js` para `Documentos\WhirlwindFX\Plugins`.
2. Rode `iniciar_ponte.bat`.
3. Opcional: rode `instalar_inicializacao.bat` para a ponte abrir junto com o Windows.

Para testar sem o SignalRGB:

```
python aoc_lightfx.py 255 0 0
```

Esse comando deixa o Light FX vermelho fixo.

### Gerar o instalador

Requer Python e [Inno Setup 6](https://jrsoftware.org/isinfo.php) (`winget install JRSoftware.InnoSetup`). Rode `instalador\build.bat`. O script empacota a ponte com o PyInstaller e gera o instalador em `instalador\Output`. Para lançar uma versão nova, altere `AppVersion` em `instalador\AOC_LightFX.iss`.

## Ícone na bandeja

O ícone mostra a cor que está sendo enviada ao monitor. Fica cinza enquanto o SignalRGB não manda cores. Clique nele para abrir o menu:

| Opção | Descrição |
|---|---|
| Iniciar com o Windows | Liga ou desliga a abertura da ponte junto com o Windows |
| Fechar o G-Menu automaticamente | Fecha o G-Menu sempre que ele abrir, porque ele disputa o monitor com a ponte. Vem ligado |
| Fechar o G-Menu agora | Fecha o G-Menu uma vez |
| Abrir log | Abre o `ponte.log` |
| Sair | Encerra a ponte |

A opção do G-Menu fica salva em `config.json`. Para usar o G-Menu de novo, desmarque a opção ou saia da ponte.

Para testar sem o SignalRGB:

```
python aoc_lightfx.py 255 0 0
```

Esse comando deixa o Light FX vermelho fixo.

## Opções no SignalRGB

| Opção | Descrição |
|---|---|
| Modo de iluminação | `Canvas` segue o efeito; `Forced` usa uma cor fixa |
| Cor forçada | Cor usada no modo Forced |
| Cor ao desligar | Cor enviada quando o SignalRGB fecha |
| Efeito do monitor | Animação feita pelo próprio monitor com as duas cores (veja abaixo). Padrão: Motion Point |
| Escolha das cores | `Mais contrastantes`: as duas cores mais diferentes entre os 8 pontos. `Esquerda / direita`: média de cada metade do anel. `Média (cor única)`: uma cor só |
| Intensidade do Light FX | Baixo, Médio ou Forte |

### Duas cores e efeito do monitor

O monitor não aceita cor por LED: ele só recebe duas cores (frente e fundo) e anima as duas com um efeito interno. No `Estático` só a cor de **fundo** aparece; nos outros efeitos as duas se misturam pelo anel.

O plugin lê 8 pontos do canvas e escolhe duas cores. Nos efeitos animados a cor só troca a cada intervalo configurado (padrão 3 s), para a animação do monitor não ficar reiniciando.

Testado com webcam no AG323FWG3R3, com frente vermelha e fundo azul:

| Efeito | O que aparece no anel |
| --- | --- |
| Motion Point | Um ponto da cor da frente gira pelo anel sobre o fundo. É o que mais lembra uma fan RGB |
| 1 Way Filling | A cor da frente vai enchendo o anel em uma direção |
| Simple Filling | Enche com a frente e volta para o fundo |
| Simple Shift, Gradient Shift, Water Wave | Ondas de brilho usando quase só a cor de fundo |
| Breathing, Flashing | O anel inteiro pulsa ou pisca |
| Zoom | Mistura frente e fundo pelo anel |
| Discolor | Ignora as cores personalizadas (muda o padrão do monitor) |

Para o anel girar com as cores do SignalRGB, use `Motion Point` com um efeito colorido como `Rainbow`.

Os efeitos da lista são os do AG323FWG3R3. Monitores com a lista nova de efeitos (Wave, Drip Fill etc.) recebem o equivalente mais próximo.

## Limitações

- **Duas cores:** o monitor recebe uma cor de frente e uma de fundo. Não dá para controlar LED por LED nem mostrar mais de duas cores ao mesmo tempo.
- **Velocidade:** o monitor descarta escritas DDC feitas a menos de ~110 ms uma da outra (a NVAPI responde sucesso mesmo assim), e depois de trocar intensidade ou efeito fica ~0,3 s ocupado. A ponte espera 120 ms entre acessos, então uma cor completa (3 canais) leva ~0,4 s e as duas cores ~0,7 s. Efeitos rápidos ficam suavizados.
- **Só NVIDIA por enquanto.** AMD (ADL) e Intel (IGCL) também têm acesso I2C; contribuições são bem-vindas.
- **G-Menu:** ele usa o mesmo barramento e disputa com a ponte. Por padrão, o ícone da bandeja fecha o G-Menu sozinho. Se o G-Menu estiver rodando como administrador, feche-o manualmente.
- **Monitor ou PC reiniciando:** desligar e ligar o monitor ou acordar o PC da suspensão ainda não foi testado. Se as luzes não voltarem, reinicie a ponte.
- Problemas ficam registrados em `ponte.log`, na pasta da ponte.

## Protocolo

Os comandos foram identificados analisando o G-Menu (AOC) e confirmados no AG323FWG3R3.

**Escrita** (endereço I2C `0x37`; byte de destino `0x6E`):

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

Escritas perdidas não dão erro, então a ponte confere o `0x60`, o `0x61` e o `0x62` lendo de volta depois de gravar e tenta de novo se não pegou.

## Aviso

Projeto não oficial, sem relação com AOC, TPV ou WhirlwindFX. Use por sua conta e risco. Os comandos são os mesmos que o G-Menu envia ao monitor.

## Licença

[MIT](LICENSE)
