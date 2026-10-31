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

- **`AOC_LightFX.js`**: o plugin do SignalRGB. Cria um dispositivo com 2 pontos (Frente e Fundo) e envia as cores para a ponte.
- **`aoc_lightfx_bridge.py`**: a ponte. Recebe as cores e grava no monitor só o que mudou, cerca de 10 atualizações por segundo. Ela também relê o monitor e corrige o que se perder.
- **`aoc_lightfx.py`**: a biblioteca DDC (NVAPI via `ctypes`, sem dependências externas).

## Requisitos

- Windows 10 ou 11
- Placa de vídeo **NVIDIA**
- **Python 3.8+** no PATH
- DDC/CI **ligado** no menu do monitor
- SignalRGB

## Instalação

1. Baixe este repositório, por exemplo para `C:\signalrgb-aoc-lightfx`.
2. Copie `AOC_LightFX.js` para a pasta de plugins do SignalRGB: `Documentos\WhirlwindFX\Plugins`.
3. Rode `iniciar_ponte.bat`. A ponte fica rodando escondida em segundo plano.
4. Opcional: rode `instalar_inicializacao.bat` para a ponte abrir junto com o Windows.
5. Reinicie o SignalRGB. O dispositivo **AOC Light FX** deve aparecer.

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
| Fundo com a mesma cor da frente | Usa só uma cor ou cores separadas para frente e fundo |
| Intensidade do Light FX | Baixo, Médio ou Forte |

## Limitações

- **Cor única:** o monitor recebe uma cor de frente e uma de fundo. Não dá para controlar LED por LED.
- **Velocidade:** cerca de 10 atualizações por segundo, porque o DDC é lento. Efeitos rápidos ficam suavizados.
- **Só NVIDIA por enquanto.** AMD (ADL) e Intel (IGCL) também têm acesso I2C; contribuições são bem-vindas.
- **Feche o G-Menu.** Ele usa o mesmo barramento e pode disputar com a ponte.
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
| `0x61` | Modo | Índice numa lista que depende do máximo informado pelo monitor (veja abaixo) |
| `0x62` | Pattern | 0 vermelho, 1 verde, 2 azul, 3 arco-íris, 4 personalizado |
| `0x63`–`0x65` | Cor da frente R/G/B | 0 até o máximo (100 no AG323FWG3R3) |
| `0x66`–`0x68` | Cor do fundo R/G/B | 0 até o máximo |

O índice do modo **Static** depende do máximo do código `0x61`: 12 → 0, 13 → 1, 14 → 2, 15 ou 16 → 3.

## Aviso

Projeto não oficial, sem relação com AOC, TPV ou WhirlwindFX. Use por sua conta e risco. Os comandos são os mesmos que o G-Menu envia ao monitor.

## Licença

[MIT](LICENSE)
