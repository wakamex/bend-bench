// Times Bend's checker and C emitter inside one Bun process, so Bun's startup
// and module loading drop out: bun time.ts BASE CANDIDATE < [[key, base_file,
// candidate_file], ...] prints {key: {base: [check, emit], candidate: [...]}}
// in seconds, or {key: {error}} for a program that fails to check or emit.
// After an untimed warmup on the first programs, each program is checked and
// emitted base, candidate, candidate, base, each step after a full garbage
// collection; a side's time is the mean of its two runs. It uses the
// checkout's own exports: Bend.book_nil, book_load and book_valid (what
// bend's CLI checks a file with) and Comp.compile_book (what -o x.c emits).
const [base, cand] = process.argv.slice(2);
const load = async (root: string) => ({
  Bend: await import(root + "/bend2/bend.ts"),
  Comp: await import(root + "/bend2/comp.ts"),
});
const sides = { base: await load(base), candidate: await load(cand) };
type Side = keyof typeof sides;

async function once(side: Side, file: string): Promise<[number, number]> {
  const { Bend, Comp } = sides[side];
  Bun.gc(true);
  let at = performance.now();
  const book = Bend.book_nil();
  await Bend.book_load(book, file, "", new Map());
  Bend.book_valid(book, 0);
  const check = performance.now() - at;
  Bun.gc(true);
  at = performance.now();
  Comp.compile_book(book);
  return [check / 1000, (performance.now() - at) / 1000];
}

const jobs: [string, string, string][] = JSON.parse(await Bun.stdin.text());
for (const [, b, c] of jobs.slice(0, 3)) {
  await once("base", b).catch(() => {});
  await once("candidate", c).catch(() => {});
}
const out: Record<string, unknown> = {};
for (const [key, b, c] of jobs) {
  const files = { base: b, candidate: c };
  const t = { base: [0, 0], candidate: [0, 0] };
  try {
    for (const side of ["base", "candidate", "candidate", "base"] as const) {
      const [check, emit] = await once(side, files[side]);
      t[side][0] += check / 2;
      t[side][1] += emit / 2;
    }
    out[key] = t;
  } catch (e) {
    out[key] = { error: String(e).split("\n")[0].slice(0, 200) };
  }
}
console.log(JSON.stringify(out));
