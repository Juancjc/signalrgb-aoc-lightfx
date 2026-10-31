// AOC AGON Light FX - envia as cores para a ponte local (aoc_lightfx_bridge.py),
// que grava no monitor via DDC/CI. A ponte precisa estar rodando.
export function Name() { return "AOC Light FX"; }
export function Version() { return "1.0.0"; }
export function Type() { return "network"; }
export function Publisher() { return "local"; }
export function Size() { return [3, 1]; }
export function DefaultPosition() { return [0, 0]; }
export function DefaultScale() { return 8.0; }
export function SubdeviceController() { return false; }
export function DefaultComponentBrand() { return "AOC"; }
export function ControllableParameters() {
	return [
		{"property":"LightingMode", "group":"lighting", "label":"Modo de iluminação", "type":"combobox", "values":["Canvas", "Forced"], "default":"Canvas"},
		{"property":"forcedColor", "group":"lighting", "label":"Cor forçada", "min":"0", "max":"360", "type":"color", "default":"#009bde"},
		{"property":"shutdownColor", "group":"lighting", "label":"Cor ao desligar", "min":"0", "max":"360", "type":"color", "default":"#000000"},
		{"property":"sameColor", "group":"lighting", "label":"Fundo com a mesma cor da frente", "type":"boolean", "default":"true"},
		{"property":"intensity", "group":"lighting", "label":"Intensidade do Light FX", "type":"combobox", "values":["Baixo", "Médio", "Forte"], "default":"Forte"},
	];
}

const BRIDGE_IP = "127.0.0.1";
const BRIDGE_PORT = 21330;
const BIG_ENDIAN = 1;
const vLedNames = ["Frente", "Fundo"];
const vLedPositions = [[0, 0], [2, 0]];

export function Initialize() {
	device.setName(controller.name);
	device.addFeature("udp");
	device.setSize([3, 1]);
	device.setControllableLeds(vLedNames, vLedPositions);
}

function hexToRgb(hex) {
	const n = parseInt(hex.replace("#", ""), 16);
	return [(n >> 16) & 0xFF, (n >> 8) & 0xFF, n & 0xFF];
}

function intensityLevel() {
	return {"Baixo": 1, "Médio": 2, "Forte": 3}[intensity] ?? 3;
}

function sendColors(front, back) {
	const packet = [0x41, 0x4F, 0x43].concat(front, back, [intensityLevel()]);
	udp.send(BRIDGE_IP, BRIDGE_PORT, packet, BIG_ENDIAN);
}

export function Render() {
	if (LightingMode === "Forced") {
		const c = hexToRgb(forcedColor);
		sendColors(c, c);

		return;
	}

	const front = device.color(vLedPositions[0][0], vLedPositions[0][1]);
	const back = sameColor ? front : device.color(vLedPositions[1][0], vLedPositions[1][1]);
	sendColors(front, back);
}

export function Shutdown(suspend) {
	const c = hexToRgb(shutdownColor);
	sendColors(c, c);
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
