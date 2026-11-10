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
    const data = await response.json();
    if (!response.ok) throw new TransportError(data.code || 'unavailable');
    return data;
  }
  create(options) { return this.request('', options); }
  snapshot(id) { return this.request(`/${encodeURIComponent(id)}`); }
  command(id, command) { return this.request(`/${encodeURIComponent(id)}/commands`, command); }
  receipt(id, command) { return this.request(`/${encodeURIComponent(id)}/receipts/${encodeURIComponent(command)}`); }
  quit(id) { return this.request(`/${encodeURIComponent(id)}/quit`, {}); }
}
// This adapter replays frozen server evidence. It never evaluates a clue or invents a score.
export class FixtureTransport {
  constructor(name = 'legality-and-target-only-clear', fetcher = globalThis.fetch.bind(globalThis)) {
    this.name = name; this.fetcher = fetcher; this.receipts = new Map();
  }
  async create() {
    const response = await this.fetcher(`/fixtures/protocol/${encodeURIComponent(this.name)}.json`);
    if (!response.ok) throw new TransportError('unavailable');
    this.frames = (await response.json()).envelopes;
    this.index = 0; this.sequence = 0; this.mapping = new Map(); this.receipts.clear();
    this.current = structuredClone(this.frames[0]);
    return structuredClone(this.current);
  }
  next() {
    this.index++;
    const frame = structuredClone(this.frames[this.index]);
    frame.sequence = ++this.sequence;
    if (frame.receipt) {
      const original = frame.receipt.command_id;
      frame.receipt.command_id = this.mapping.get(original) || original;
      this.receipts.set(frame.receipt.command_id, structuredClone(frame.receipt));
    }
    if (frame.snapshot.pending) frame.snapshot.pending.command_id =
      this.mapping.get(frame.snapshot.pending.command_id) || frame.snapshot.pending.command_id;
    this.current = frame;
    return structuredClone(frame);
  }
  async command(id, command) {
    if (this.receipts.has(command.command_id)) return this.receipt(id, command.command_id);
    const frame = this.frames.slice(this.index + 1).find(item => item.receipt);
    if (!frame) return structuredClone(this.current);
    if (frame.receipt) this.mapping.set(frame.receipt.command_id, command.command_id);
    return this.next();
  }
  async snapshot() {
    const next = this.frames[this.index + 1];
    // Pause before new commands; spawns and an admitted command's completion continue.
    if (next && (!next.receipt || this.mapping.has(next.receipt.command_id))) return this.next();
    return structuredClone(this.current);
  }
  async receipt(id, command) {
    const receipt = this.receipts.get(command);
    if (!receipt) throw new TransportError('receipt_not_found');
    return { ...structuredClone(this.current), receipt: structuredClone(receipt) };
  }
  async quit() {
    throw new TransportError('fixture_quit');
  }
}
