export class TransportError extends Error {
  constructor(code) { super(code); this.code = code; }
}
export class HttpTransport {
  constructor(fetcher = globalThis.fetch.bind(globalThis)) { this.fetcher = fetcher; }
  async request(path, body) {
    const response = await this.fetcher(`/experiment/v1/games${path}`, {
      method: body === undefined ? 'GET' : 'POST',
      headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(8000), cache: 'no-store',
    });
    let data;
    try { data = await response.json(); }
    catch { throw new TransportError('unavailable'); }
    if (!data || typeof data !== 'object' || Array.isArray(data)) throw new TransportError('unavailable');
    if (!response.ok) throw new TransportError(data.code || 'unavailable');
    return data;
  }
  create(options) { return this.request('', options); }
  snapshot(id) { return this.request(`/${encodeURIComponent(id)}`); }
  command(id, command) { return this.request(`/${encodeURIComponent(id)}/commands`, command); }
  receipt(id, command) { return this.request(`/${encodeURIComponent(id)}/receipts/${encodeURIComponent(command)}`); }
  quit(id) { return this.request(`/${encodeURIComponent(id)}/quit`, {}); }
}
