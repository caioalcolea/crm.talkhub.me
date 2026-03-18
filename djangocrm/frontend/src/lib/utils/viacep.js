/**
 * ViaCEP integration — auto-fill address from Brazilian CEP (zip code)
 * API: https://viacep.com.br/ws/{CEP}/json/ (free, no auth)
 */

/**
 * Busca endereço pelo CEP via ViaCEP API
 * @param {string} cep - CEP com ou sem formatação (aceita 01001-000 ou 01001000)
 * @returns {Promise<{addressLine: string, city: string, state: string, postcode: string, country: string} | null>}
 */
export async function fetchAddressByCep(cep) {
	const cleanCep = cep.replace(/\D/g, '');
	if (cleanCep.length !== 8) return null;

	try {
		const response = await fetch(`https://viacep.com.br/ws/${cleanCep}/json/`, {
			signal: AbortSignal.timeout(5000)
		});
		if (!response.ok) return null;

		const data = await response.json();
		if (data.erro) return null;

		const parts = [data.logradouro, data.bairro].filter(Boolean);
		return {
			addressLine: parts.join(', '),
			city: data.localidade || '',
			state: data.uf || '',
			postcode: data.cep || cleanCep,
			country: 'BR'
		};
	} catch {
		return null;
	}
}
