import { GameStore, validateClue } from './store.mjs';
const enc = encodeURIComponent;
export class ApiError extends Error {
  constructor(code, status = 0) { super(code); this.code = code; this.status = status; }
}
export class DurableTransport {
  constructor(fetcher = globalThis.fetch.bind(globalThis)) { this.fetcher = fetcher; this.csrf = null; }
  async request(path, body, method = body === undefined ? 'GET' : 'POST') {
    const headers = body === undefined ? {} : { 'Content-Type': 'application/json' };
    if (method !== 'GET' && this.csrf) headers['X-CSRF-Token'] = this.csrf;
    let response;
    try {
      response = await this.fetcher(`/api/v1${path}`, { method,
        body: body === undefined ? undefined : JSON.stringify(body), headers,
        credentials: 'same-origin', cache: 'no-store', signal: AbortSignal.timeout(8000) });
    } catch { throw new ApiError('unavailable'); }
    if (response.status === 204) return null;
    let value;
    try { value = await response.json(); } catch { throw new ApiError('unavailable'); }
    if (!value || typeof value !== 'object' || Array.isArray(value)) throw new ApiError('unavailable');
    if (!response.ok) throw new ApiError(value.code || 'unavailable', response.status);
    return value;
  }
}
export class DurableClient {
  constructor(transport) {
    this.transport = transport; this.store = new GameStore(); this.session = null;
    this.generation = 0; this.creationUncertain = false; this.uncertainAccountId = null; this.busy = false; this.boardQuery = null;
  }
  async request(path, body, method = body === undefined ? 'GET' : 'POST') {
    const generation = this.generation;
    try {
      const value = await this.transport.request(path, body, method);
      if (generation !== this.generation) throw new ApiError('session_changed');
      return value;
    }
    catch (error) {
      if (generation !== this.generation) throw new ApiError('session_changed');
      if (error.status === 401 && generation === this.generation) this.clearPrivate({ preserveCreation: true });
      throw error;
    }
  }
  clearPrivate({ preserveCreation = false } = {}) {
    if (!preserveCreation) { this.creationUncertain = false; this.uncertainAccountId = null; }
    this.generation++; this.session = null; this.transport.csrf = null; this.store = new GameStore();
    this.boardQuery = null;
  }
  async authenticate(kind, body) {
    const value = await this.request(`/auth/${kind}`, body);
    const preserveCreation = this.creationUncertain && this.uncertainAccountId === value.account.account_id;
    this.clearPrivate({ preserveCreation }); this.session = value; this.transport.csrf = value.csrf_token;
    return value;
  }
  async restore() {
    const value = await this.request('/auth/session');
    if (this.session?.account.account_id !== value.account.account_id) {
      const preserveCreation = this.creationUncertain && this.uncertainAccountId === value.account.account_id;
      this.clearPrivate({ preserveCreation });
    }
    this.session = value; this.transport.csrf = value.csrf_token; return value;
  }
  async logout() { await this.request('/auth/logout', undefined, 'POST'); this.clearPrivate(); }
  async create(artifact, explicitNew = false) {
    if (this.busy || (this.creationUncertain && !explicitNew)) throw new ApiError('creation_uncertain');
    this.busy = true;
    try {
      const envelope = await this.request('/games', { mode: 'casual', artifact_id: artifact });
      if (this.store.snapshot?.game_id !== envelope.snapshot.game_id) this.store = new GameStore();
      this.store.apply(envelope); this.creationUncertain = false; this.uncertainAccountId = null;
      return envelope;
    } catch (error) {
      // A lost or server-error response cannot prove that the create did not commit.
      if (error.code !== 'session_changed' && (!error.status || error.status >= 500)) {
        this.creationUncertain = true; this.uncertainAccountId = this.session?.account.account_id ?? null;
      }
      throw error;
    } finally { this.busy = false; }
  }
  async discover() {
    const envelope = await this.request('/games/current');
    if (this.store.snapshot?.game_id !== envelope.snapshot.game_id) this.store = new GameStore();
      this.store.apply(envelope); this.creationUncertain = false; this.uncertainAccountId = null;
    return envelope;
  }
  async send(clue, id = globalThis.crypto.randomUUID()) {
    const problem = validateClue(clue); if (problem) throw new Error(problem);
    const command = this.store.command(clue, id); if (!command) throw new ApiError('command_pending');
    return this.retryCommand();
  }
  async retryCommand() {
    const command = this.store.pending;
    if (!command) return;
    const envelope = await this.request(`/games/${enc(this.store.snapshot.game_id)}/commands`, command);
    return this.store.apply(envelope);
  }
  async refresh() {
    const snapshot = this.store.snapshot; if (!snapshot) return;
    const command = this.store.pending?.command_id || snapshot.pending?.command_id;
    const path = `/games/${enc(snapshot.game_id)}` + (command ? `/receipts/${enc(command)}` : '');
    try { return this.store.apply(await this.request(path)); }
    catch (error) {
      // Unknown receipt after a network failure permits an explicit exact retry only.
      if (error.status === 410) { this.store.pending = null; this.store.snapshot = null; }
      throw error;
    }
  }
  async quit() {
    return this.store.apply(await this.request(`/games/${enc(this.store.snapshot.game_id)}/quit`, {}));
  }
  page(path, cursor) { return this.request(path + (cursor ? `?cursor=${enc(cursor)}` : '')); }
  async board(artifact, cursor = null) {
    if (cursor && this.boardQuery !== artifact) throw new ApiError('invalid_cursor');
    const result = await this.page(`/boards/${enc(artifact)}`, cursor);
    this.boardQuery = artifact; return result;
  }
}

// Deliberately scripted fixture transport, not an authentication or game implementation.
export class FixtureTransport {
  constructor(payloads, script) {
    this.values = new Map(payloads.cases.map(item => [item.name, item.value]));
    this.script = [...script]; this.calls = []; this.csrf = null;
  }
  async request(path, body, method = body === undefined ? 'GET' : 'POST') {
    this.calls.push({ path, body: structuredClone(body) });
    const step = this.script.shift();
    if (!step || step.path !== path) throw new Error(`Unexpected fixture request: ${path}`);
    if (step.networkError) throw new ApiError('unavailable');
    const value = structuredClone(this.values.get(step.response));
    if (step.status >= 400) throw new ApiError(value?.code || step.response, step.status);
    return value;
  }
}
