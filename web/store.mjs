export const clueLength = text => [...text].length;
export function validateClue(text) {
  if (!text.trim()) return 'Type a clue first.';
  if (clueLength(text) > 120) return 'Use 120 characters or fewer.';
  return '';
}
export function resultText(receipt) {
  const messages = {
    stale_revision: 'The target changed. Check it before sending again.',
    no_target: 'Next word arriving soon.', clue_empty: 'Type a clue first.',
    clue_too_long: 'Use 120 characters or fewer.',
    clue_control_character: 'Remove control characters from your clue.',
    clue_forbidden: 'Try an association without the target word or its forbidden forms.',
    inference_failed: 'That clue could not be ranked. Try again.',
    inference_timeout: 'Ranking took too long. Try again.',
    overloaded: 'The game is busy. Try again.',
    command_conflict: 'That command could not be reconciled. Reconnect before sending again.',
    game_over: 'The game has ended.',
  };
  if (receipt.outcome === 'clear') return `Target reached #${receipt.target_rank} — +${receipt.score_delta}.`;
  if (receipt.outcome === 'miss') return `Target reached #${receipt.target_rank}. Try another association.`;
  return messages[receipt.outcome] || 'Ranking your clue…';
}
export class GameStore {
  constructor() { this.snapshot = null; this.pending = null; this.seen = new Set(); }
  apply(envelope) {
    if (envelope.protocol !== 'experiment-v1') throw new Error('unsupported_protocol');
    const incoming = envelope.snapshot;
    if (this.snapshot && incoming.game_id !== this.snapshot.game_id) return {};
    const previous = this.snapshot;
    const accepted = !previous || incoming.revision > previous.revision ||
      (incoming.revision === previous.revision && incoming.elapsed_ms >= previous.elapsed_ms);
    if (accepted) this.snapshot = incoming;
    const receipt = envelope.receipt;
    let result = null;
    if (receipt && !['pending', 'busy'].includes(receipt.outcome) && !this.seen.has(receipt.command_id)) {
      this.seen.add(receipt.command_id);
      if (this.pending?.command_id === receipt.command_id) {
        result = receipt;
        this.pending = null;
      }
    }
    if (this.snapshot?.status === 'over') this.pending = null;
    return { accepted, result, gap: !!previous && incoming.revision > previous.revision + 1 };
  }
  command(clue, id) {
    if (this.pending || this.snapshot.pending || this.snapshot.status !== 'active' || !this.snapshot.target) return null;
    const command = { command_id: id, expected_revision: this.snapshot.revision, clue };
    this.pending = command;
    return command;
  }
}
