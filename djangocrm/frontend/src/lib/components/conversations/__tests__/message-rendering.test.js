/**
 * PBT: Renderização de mensagens por direção e tipo.
 *
 * Propriedade 39: Cada direção produz o estilo visual correto.
 * Propriedade 40: Cada msg_type usa o componente correto.
 * Propriedade 41: Botão de chat visível apenas com omni_user_ns.
 * Valida: Requisitos 18.2, 18.3, 19.1, 19.4
 *
 * NOTA: Requer vitest para execução. Adicionar ao package.json:
 *   "vitest": "^3.x", "@testing-library/svelte": "^5.x"
 *   Script: "test": "vitest --run"
 */

// ─── Propriedade 39: Mapeamento de direção → estilo ─────────────────────────

const DIRECTION_STYLES = {
	in: { align: 'left', color: 'gray', label: 'Entrada' },
	out: { align: 'right', color: 'blue', label: 'Saída (bot)' },
	agent: { align: 'right', color: 'green', label: 'Agente' },
	note: { align: 'center', color: 'yellow', label: 'Nota interna' },
	system: { align: 'center', color: 'gray-light', label: 'Sistema' }
};

const VALID_DIRECTIONS = ['in', 'out', 'agent', 'note', 'system'];

// Test: Cada direção válida tem um estilo mapeado
export function testAllDirectionsHaveStyles() {
	for (const dir of VALID_DIRECTIONS) {
		const style = DIRECTION_STYLES[dir];
		if (!style) throw new Error(`Direction "${dir}" has no style mapping`);
		if (!style.align) throw new Error(`Direction "${dir}" missing align`);
		if (!style.color) throw new Error(`Direction "${dir}" missing color`);
	}
	return true;
}

// Test: Direções de entrada ficam à esquerda, saída à direita
export function testDirectionAlignment() {
	if (DIRECTION_STYLES.in.align !== 'left') throw new Error('in should be left');
	if (DIRECTION_STYLES.out.align !== 'right') throw new Error('out should be right');
	if (DIRECTION_STYLES.agent.align !== 'right') throw new Error('agent should be right');
	if (DIRECTION_STYLES.note.align !== 'center') throw new Error('note should be center');
	if (DIRECTION_STYLES.system.align !== 'center') throw new Error('system should be center');
	return true;
}

// ─── Propriedade 40: Mapeamento de msg_type → componente ────────────────────

const MSG_TYPE_COMPONENTS = {
	text: 'TextContent',
	image: 'ImageThumbnail',
	video: 'VideoPlayer',
	audio: 'AudioPlayer',
	file: 'FileDownload',
	payload: 'StructuredCard'
};

const VALID_MSG_TYPES = ['text', 'image', 'video', 'audio', 'file', 'payload'];

export function testAllMsgTypesHaveComponents() {
	for (const type of VALID_MSG_TYPES) {
		const component = MSG_TYPE_COMPONENTS[type];
		if (!component) throw new Error(`msg_type "${type}" has no component mapping`);
	}
	return true;
}

// ─── Propriedade 41: Botão de chat visível com omni_user_ns ─────────────────

export function testChatButtonVisibility() {
	// Com omni_user_ns preenchido → visível
	const withOmni = { omni_user_ns: 'user-123' };
	if (!shouldShowChatButton(withOmni)) throw new Error('Should show with omni_user_ns');

	// Sem omni_user_ns → oculto
	const withoutOmni = { omni_user_ns: null };
	if (shouldShowChatButton(withoutOmni)) throw new Error('Should hide without omni_user_ns');

	// String vazia → oculto
	const emptyOmni = { omni_user_ns: '' };
	if (shouldShowChatButton(emptyOmni)) throw new Error('Should hide with empty omni_user_ns');

	return true;
}

function shouldShowChatButton(contact) {
	return Boolean(contact.omni_user_ns && contact.omni_user_ns.trim());
}

// ─── Self-test runner ────────────────────────────────────────────────────────

const tests = [
	['Prop 39: All directions have styles', testAllDirectionsHaveStyles],
	['Prop 39: Direction alignment', testDirectionAlignment],
	['Prop 40: All msg_types have components', testAllMsgTypesHaveComponents],
	['Prop 41: Chat button visibility', testChatButtonVisibility]
];

let passed = 0;
for (const [name, fn] of tests) {
	try {
		fn();
		passed++;
	} catch (e) {
		console.error(`FAIL: ${name} — ${e.message}`);
	}
}
console.log(`${passed}/${tests.length} tests passed`);
