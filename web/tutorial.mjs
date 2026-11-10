// An isolated warm-up: no server session or gameplay clock exists until it ends.
export class TutorialTransport {
  constructor() { this.step = 0; this.done = false; this.receipts = new Map(); }
  note(typing = false) {
    if (this.done) return 'Ready. Start the game when you are.';
    return typing ? 'Press Enter to try your clue. The clock is paused.' : [
      'This is your target. Type “orbit” to connect to moon. Take your time.',
      'A new word drops only when you engage. Try “ocean” for wave.',
      'Try “forest” for tree. In casual play, five successful clues sweep the clear zone; eligible targets then cascade.'
    ][this.step];
  }
  async create() {
    this.current = { protocol: 'experiment-v1', sequence: 0, receipt: null, snapshot: {
      game_id: 'warm-up', identities: { ruleset_id: 'tutorial', pack_digest: 'Guided warm-up', model_fingerprint: 'Scripted examples' },
      mode: 'casual', board: ['moon'], target: 'moon', entries: { moon: {label:'moon'}, wave: {label:'wave'}, tree: {label:'tree'} },
      capacity: 20, zone_size: 3, score: 0, clears: 0, level: 1, revision: 0, elapsed_ms: 0,
      next_spawn_ms: null, status: 'active', pending: null, end_reason: null
    }};
    return this.snapshot();
  }
  async snapshot() { return structuredClone(this.current); }
  async command(id, command) {
    if (this.receipts.has(command.command_id)) return structuredClone(this.receipts.get(command.command_id));
    if (this.done) return this.snapshot();
    const s = this.current.snapshot, target = s.target;
    const accepted = command.clue.trim().toLowerCase() === ['orbit','ocean','forest'][this.step];
    s.revision++;
    if (accepted) {
      this.step++; this.done = this.step === 3;
      s.target = ['moon','wave','tree'][this.step] || null; s.board = s.target ? [s.target] : [];
    }
    this.current.receipt = { command_id: command.command_id, outcome: accepted ? 'clear' : 'miss', target,
      target_rank: accepted ? 1 : 4, score_delta: 0, clear_waves: accepted ? [[target]] : [] };
    const envelope = await this.snapshot(); this.receipts.set(command.command_id, envelope); return envelope;
  }
}
