# CPU and GPU summation scaling

Complete-program times include startup, generating the integers, wrapping-U32 summation and scalar output. All implementations generate inputs during reduction, without an input array. Each cell is the median of ten checked executions after two warmups. Implementation order is shuffled within each repetition.

| Generated integers | Bend CPU1 seconds | Bend CPU16 seconds | Bend GPU seconds | Serial C++ seconds | OpenMP16 seconds | CUB seconds |
|---|---:|---:|---:|---:|---:|---:|
| 268,435,456 | 1.285711 | 0.101275 | 0.164607 | 0.059221 | 0.008350 | 0.207267 |
| 536,870,912 | 2.495672 | 0.193607 | 0.192227 | 0.114566 | 0.012294 | 0.208816 |
| 1,073,741,824 | 4.718810 | 0.329994 | 0.245207 | 0.225161 | 0.018639 | 0.206902 |
| 2,147,483,648 | 9.718447 | 0.759578 | 0.366879 | 0.449903 | 0.044382 | 0.211267 |

All sizes use the same balanced Bend reduction and the same deterministic input sequence. The new CPU controls fuse input generation and summation; the older serial control allocated and populated an input array. These are new matched measurements, not CPU values added to earlier GPU runs. Each size is checked against a separate scalar reference. CUB receives an explicit unsigned 64-bit item count, selecting 64-bit offsets in the pinned library, including at 2^31.

Bend revision and patches, host configuration, compiler flags, prepared sources, binaries, linked-library hashes and individual measurements are preserved beside this report. The existing shared benchmark lock and GPU activity policy apply. The finite sweep has a two-hour measurement budget and a 180-second timeout per execution. Failed attempts remain archived.
