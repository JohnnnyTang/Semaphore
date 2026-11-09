// Independent binary64 rank implementation. stdin/stdout only; no files or network.
let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', () => {
  const cases = JSON.parse(input);
  const output = cases.map(({query, entries}) => {
    const scores = Object.fromEntries(Object.entries(entries).map(([id, vector]) => {
      if (query.length !== 2560 || vector.length !== 2560) throw Error('dimension');
      let score = 0;
      for (let i = 0; i < 2560; i++) score = score + query[i] * vector[i];
      if (!Number.isFinite(score)) throw Error('nonfinite');
      return [id, score];
    }));
    const ordered = Object.keys(scores).sort((a, b) => {
      const diff = Math.floor(scores[b] / 0.00001 + 0.5) - Math.floor(scores[a] / 0.00001 + 0.5);
      return diff || (a < b ? -1 : a > b ? 1 : 0);
    });
    return {scores, ordered};
  });
  process.stdout.write(JSON.stringify(output));
});
