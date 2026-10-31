// AOC AGON Light FX - envia as cores para a ponte local (aoc_lightfx_bridge.py),
// que grava no monitor via DDC/CI. A ponte precisa estar rodando.
//
// O monitor só aceita duas cores (frente e fundo) e anima as duas com um efeito
// interno. O plugin lê a área do dispositivo (grade 5x5) e escolhe as duas cores.
export function Name() { return "AOC Light FX"; }
export function Version() { return "1.2.0"; }
export function Type() { return "network"; }
export function Publisher() { return "local"; }
export function Size() { return [5, 5]; }
export function DefaultPosition() { return [0, 0]; }
export function DefaultScale() { return 8.0; }
export function SubdeviceController() { return false; }
export function DefaultComponentBrand() { return "AOC"; }

// Nomes mostrados no SignalRGB; o índice é o código do efeito enviado à ponte.
const EFFECTS = [
	"Estático", "Simple Shift", "Gradient Shift", "Simple Filling", "1 Way Filling", "2 Way Filling",
	"Breathing", "Motion Point", "Zoom", "Discolor", "Water Wave", "Flashing",
];

export function ControllableParameters() {
	return [
		{"property":"LightingMode", "group":"lighting", "label":"Modo de iluminação", "type":"combobox", "values":["Canvas", "Forced"], "default":"Canvas"},
		{"property":"forcedColor", "group":"lighting", "label":"Cor forçada", "min":"0", "max":"360", "type":"color", "default":"#009bde"},
		{"property":"shutdownColor", "group":"lighting", "label":"Cor ao desligar", "min":"0", "max":"360", "type":"color", "default":"#000000"},
		{"property":"effect", "group":"lighting", "label":"Efeito do monitor", "type":"combobox", "values":EFFECTS, "default":"Motion Point"},
		{"property":"colorPick", "group":"lighting", "label":"Escolha das cores", "type":"combobox", "values":["Mais contrastantes", "Esquerda / direita", "Média (cor única)"], "default":"Mais contrastantes"},
		{"property":"swapInterval", "group":"lighting", "label":"Troca de cor nos efeitos animados", "type":"combobox", "values":["Rápida (pode piscar)", "1 s", "3 s", "6 s"], "default":"3 s"},
		{"property":"intensity", "group":"lighting", "label":"Intensidade do Light FX", "type":"combobox", "values":["Baixo", "Médio", "Forte"], "default":"Forte"},
	];
}

const BRIDGE_IP = "127.0.0.1";
const BRIDGE_PORT = 21330;
const BIG_ENDIAN = 1;
// anel de 8 pontos numa grade 5x5, no sentido horário a partir do topo
const vLedPositions = [[1, 0], [3, 0], [4, 1], [4, 3], [3, 4], [1, 4], [0, 3], [0, 1]];
const vLedNames = vLedPositions.map((_, i) => `Anel ${i + 1}`);
const GRID = 5;
// pontos com todos os canais abaixo disso contam como apagados
const DARK = 30;
// diferença mínima (distância RGB ao quadrado) para trocar a cor num efeito animado
const MIN_CHANGE = 50 * 50;

let prevFront = null;
let prevBack = null;
let heldFront = null;
let heldBack = null;
let lastSwap = 0;

export function Initialize() {
	device.setName(controller.name);
	device.addFeature("udp");
	device.setSize([5, 5]);
	device.setControllableLeds(vLedNames, vLedPositions);
}

function hexToRgb(hex) {
	const n = parseInt(hex.replace("#", ""), 16);
	return [(n >> 16) & 0xFF, (n >> 8) & 0xFF, n & 0xFF];
}

function intensityLevel() {
	return {"Baixo": 1, "Médio": 2, "Forte": 3}[intensity] ?? 3;
}

function effectCode() {
	const i = EFFECTS.indexOf(effect);

	return i < 0 ? 0 : i;
}

function dist(a, b) {
	const dr = a[0] - b[0], dg = a[1] - b[1], db = a[2] - b[2];

	return dr * dr + dg * dg + db * db;
}

function average(colors) {
	const sum = [0, 0, 0];

	for (const c of colors) {
		sum[0] += c[0]; sum[1] += c[1]; sum[2] += c[2];
	}

	return sum.map(v => Math.round(v / colors.length));
}

// Par de amostras mais diferentes entre si. Cada cor final é a média das amostras
// mais próximas dela, para não depender de um único ponto.
function contrastingPair(samples) {
	let a = 0, b = 0, best = -1;

	for (let i = 0; i < samples.length; i++) {
		for (let j = i + 1; j < samples.length; j++) {
			const d = dist(samples[i], samples[j]);

			if (d > best) { best = d; a = i; b = j; }
		}
	}

	const groupA = [], groupB = [];

	for (const s of samples) {
		(dist(s, samples[a]) <= dist(s, samples[b]) ? groupA : groupB).push(s);
	}

	return [average(groupA), average(groupB)];
}

function isLit(c) {
	return Math.max(c[0], c[1], c[2]) >= DARK;
}

// Leva a cor ao brilho máximo mantendo o tom: verde-escuro e verde-claro viram o
// mesmo verde, então a escolha das duas cores compara tons, não brilho.
function vivid(c) {
	const max = Math.max(c[0], c[1], c[2]);

	if (max < DARK) {
		return [0, 0, 0];
	}

	return c.map(v => Math.round(v * 255 / max));
}

// Cores avivadas dos pontos acesos da grade (todas as colunas ou só algumas).
// Sem nenhum ponto aceso, devolve preto.
function sampleGrid(columns) {
	const colors = [];

	for (const x of columns) {
		for (let y = 0; y < GRID; y++) {
			const c = device.color(x, y);

			if (isLit(c)) {
				colors.push(vivid(c));
			}
		}
	}

	return colors.length ? colors : [[0, 0, 0]];
}

function sampleColors() {
	const samples = sampleGrid([0, 1, 2, 3, 4]);

	if (colorPick === "Média (cor única)") {
		const c = vivid(average(samples));

		return [c, c];
	}

	if (colorPick === "Esquerda / direita") {
		const left = vivid(average(sampleGrid([0, 1])));
		const right = vivid(average(sampleGrid([3, 4])));

		return [isLit(left) ? left : right, isLit(right) ? right : left];
	}

	let [front, back] = contrastingPair(samples);
	front = vivid(front);
	back = vivid(back);

	// mantém cada cor no mesmo papel (frente/fundo) entre quadros, para não ficar trocando
	if (prevFront && dist(front, prevFront) + dist(back, prevBack) > dist(back, prevFront) + dist(front, prevBack)) {
		[front, back] = [back, front];
	}

	return [front, back];
}

function swapMs() {
	return {"Rápida (pode piscar)": 0, "1 s": 1000, "3 s": 3000, "6 s": 6000}[swapInterval] ?? 3000;
}

// O monitor recomeça a animação quando a cor muda. Nos efeitos animados a cor só
// troca quando muda de verdade e no máximo a cada swapMs(), para a animação rodar.
function holdColors(front, back) {
	const now = Date.now();
	const interval = effectCode() === 0 ? 0 : swapMs();
	const changed = heldFront === null ||
		Math.max(dist(front, heldFront), dist(back, heldBack)) >= MIN_CHANGE;

	if (interval === 0 || (changed && now - lastSwap >= interval)) {
		heldFront = front;
		heldBack = back;
		lastSwap = now;
	}

	return [heldFront, heldBack];
}

function sendColors(front, back) {
	prevFront = front;
	prevBack = back;
	const packet = [0x41, 0x4F, 0x43].concat(front, back, [intensityLevel(), effectCode()]);
	udp.send(BRIDGE_IP, BRIDGE_PORT, packet, BIG_ENDIAN);
}

export function Render() {
	if (LightingMode === "Forced") {
		const c = hexToRgb(forcedColor);
		sendColors(c, c);

		return;
	}

	const [front, back] = holdColors(...sampleColors());
	sendColors(front, back);
}

export function Shutdown(suspend) {
	const c = hexToRgb(shutdownColor);
	const packet = [0x41, 0x4F, 0x43].concat(c, c, [intensityLevel(), 0]);
	udp.send(BRIDGE_IP, BRIDGE_PORT, packet, BIG_ENDIAN);
}

// O dispositivo é sempre local: anuncia um controlador fixo apontando para a ponte.
export function DiscoveryService() {
	this.IconUrl = "";
	this.announced = false;

	this.Initialize = function() {
		service.log("AOC Light FX: registrando dispositivo local");
	};

	this.Update = function() {
		if (this.announced) {
			return;
		}

		let ctrl = service.getController("aoc-lightfx-local");

		if (ctrl === undefined) {
			ctrl = new AOCLightFXController();
			service.addController(ctrl);
		}

		service.announceController(ctrl);
		this.announced = true;
	};

	this.Discovered = function(value) {};
}

class AOCLightFXController {
	constructor() {
		this.id = "aoc-lightfx-local";
		this.name = "AOC Light FX";
		this.ip = BRIDGE_IP;
	}

	update() {}

	updateWithValue(value) {}
}
