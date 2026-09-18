"""Host-ready timing adapter for the pinned generated MNK runtime."""
from array import array
from pathlib import Path


def instrument(source, count):
    marker = '  WL_CASE(FID_EMIT)\n  {\n    Term a_0 = r0;'
    if source.count(marker) != 1:
        raise ValueError('Generated emit layout changed')
    at = source.index('#define CID_ANSWER ')
    source = source[:at] + '#if !DEVICE\nstatic Term host_answer;\nstatic bool host_pending;\n#endif\n' + source[at:]
    source = source.replace(marker, marker + '\n    host_answer = a_0; host_pending = true;')
    old = '''Term io_now_run(Env e, Term* f, IoWork* w) {
  return (Term)(io_tick() / 1000000);
}'''
    if source.count(old) != 1:
        raise ValueError('Generated clock effect changed')
    new = r'''
static uint32_t *host_answers;
static FILE *host_file;
static u64 host_start;
static size_t host_count;

static void host_flatten(Env e, Term t) {
  if (term_aux(t) == CID_ANSWER) {
    if (host_count >= @COUNT@) err_fail("too many host answers");
    host_answers[host_count++] = (uint32_t)term_loc(t);
  } else if (term_aux(t) == CID_BOTH) {
    Loc p = term_loc(t);
    host_flatten(e, e.mem[p]);
    host_flatten(e, e.mem[p + 1]);
  } else {
    err_fail("unfinished or invalid answer tree");
  }
}

Term io_now_run(Env e, Term* f, IoWork* w) {
  if (host_answers == NULL) {
    host_answers = malloc(@COUNT@ * sizeof(uint32_t));
    if (host_answers == NULL) err_fail("host answer allocation failed");
    for (size_t i = 0; i < @COUNT@; ++i) ((volatile uint32_t*)host_answers)[i] = 0;
    const char *path = getenv("BEND_BENCH_HOST_ARRAY");
    if (path == NULL || (host_file = fopen(path, "wb")) == NULL)
      err_fail("host answer evidence path unavailable");
  }
  if (host_pending) {
    host_count = 0;
    host_flatten(e, host_answer);
    if (host_count != @COUNT@) err_fail("missing host answers");
    u64 ready = io_tick();
    // Evidence writes happen after the host-ready timestamp.
    fprintf(stderr, "HOST_READY_NS %llu %llu\n", (unsigned long long)host_start, (unsigned long long)ready);
    if (fwrite(host_answers, sizeof(uint32_t), host_count, host_file) != host_count || fflush(host_file))
      err_fail("host answer evidence write failed");
    host_pending = false;
    return (Term)(ready / 1000000);
  }
  host_start = io_tick();
  return (Term)(host_start / 1000000);
}
'''.replace('@COUNT@', str(count))
    return source.replace(old, new)


def validate(path, expected, count, total):
    """Compare every saved uint32 with the independent rotated corpus."""
    if array('I').itemsize != 4:
        raise ValueError('Host uint32 representation unsupported')
    with Path(path).open('rb') as stream:
        for rep in range(total):
            rotation = (11 - rep) % len(expected)
            pattern = expected[rotation:] + expected[:rotation]
            wanted = array('I', (pattern * ((count + len(pattern) - 1) // len(pattern)))[:count]).tobytes()
            if stream.read(count * 4) != wanted:
                raise ValueError(f'Host array mismatch in batch {rep}')
        if stream.read(1):
            raise ValueError('Trailing host array data')
