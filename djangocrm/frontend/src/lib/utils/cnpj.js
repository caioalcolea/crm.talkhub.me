/**
 * CNPJ utilities — validation, formatting, and BrasilAPI lookup
 * API: https://brasilapi.com.br/api/cnpj/v1/{CNPJ} (free, no auth)
 */

/**
 * Valida dígitos verificadores do CNPJ
 * @param {string} cnpj - CNPJ com ou sem formatação
 * @returns {boolean}
 */
export function validateCnpj(cnpj) {
	const clean = cnpj.replace(/\D/g, '');
	if (clean.length !== 14) return false;
	if (/^(\d)\1{13}$/.test(clean)) return false; // Todos dígitos iguais

	const weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
	const weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];

	let sum = 0;
	for (let i = 0; i < 12; i++) sum += parseInt(clean[i]) * weights1[i];
	let remainder = sum % 11;
	const digit1 = remainder < 2 ? 0 : 11 - remainder;
	if (parseInt(clean[12]) !== digit1) return false;

	sum = 0;
	for (let i = 0; i < 13; i++) sum += parseInt(clean[i]) * weights2[i];
	remainder = sum % 11;
	const digit2 = remainder < 2 ? 0 : 11 - remainder;
	if (parseInt(clean[13]) !== digit2) return false;

	return true;
}

/**
 * Formata CNPJ: 00000000000000 → 00.000.000/0000-00
 * @param {string} cnpj
 * @returns {string}
 */
export function formatCnpj(cnpj) {
	const clean = cnpj.replace(/\D/g, '');
	if (clean.length !== 14) return cnpj;
	return clean.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5');
}

/**
 * Formata telefone da BrasilAPI: "1133334444" → "(11) 3333-4444"
 * @param {string} raw
 * @returns {string}
 */
function formatPhone(raw) {
	if (!raw) return '';
	const clean = raw.replace(/\D/g, '');
	if (clean.length === 10) {
		return clean.replace(/^(\d{2})(\d{4})(\d{4})$/, '($1) $2-$3');
	}
	if (clean.length === 11) {
		return clean.replace(/^(\d{2})(\d{5})(\d{4})$/, '($1) $2-$3');
	}
	return raw;
}

/**
 * Converte string UPPER CASE para Title Case
 * @param {string} str
 * @returns {string}
 */
function toTitleCase(str) {
	if (!str) return '';
	return str
		.toLowerCase()
		.replace(/(?:^|\s|[-/])\w/g, (match) => match.toUpperCase());
}

/**
 * Busca dados da empresa pelo CNPJ via BrasilAPI
 * @param {string} cnpj - CNPJ (com ou sem formatação)
 * @returns {Promise<{name: string, addressLine: string, city: string, state: string, postcode: string, country: string, phone: string, email: string, cnpj: string} | null>}
 */
export async function fetchCompanyByCnpj(cnpj) {
	const clean = cnpj.replace(/\D/g, '');
	if (clean.length !== 14) return null;

	try {
		const response = await fetch(`https://brasilapi.com.br/api/cnpj/v1/${clean}`, {
			signal: AbortSignal.timeout(10000)
		});
		if (!response.ok) return null;

		const data = await response.json();

		// Build address line: logradouro, numero - bairro
		const addrParts = [data.logradouro];
		if (data.numero && data.numero !== 'SN') addrParts.push(data.numero);
		let addressLine = addrParts.join(', ');
		if (data.bairro) addressLine += ` - ${data.bairro}`;

		return {
			name: toTitleCase(data.razao_social || ''),
			addressLine,
			city: toTitleCase(data.municipio || ''),
			state: data.uf || '',
			postcode: data.cep ? data.cep.replace(/\D/g, '').replace(/^(\d{5})(\d{3})$/, '$1-$2') : '',
			country: 'BR',
			phone: formatPhone(data.ddd_telefone_1 || ''),
			email: (data.email || '').toLowerCase().trim(),
			cnpj: formatCnpj(clean)
		};
	} catch {
		return null;
	}
}
