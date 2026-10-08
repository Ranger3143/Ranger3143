"""VERIFY-2: sample of the 164 receipts minted by `cis_witness gen` (SAFE-01 H2) through the new binary, default and --strict, against their own (mutated) model."""
import os, re, glob, random, subprocess, collections
from concurrent.futures import ThreadPoolExecutor
R = '/home/user/Ranger3143'; S = '/tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad'
NEW = '/home/user/aefinity-ai/alice-aegis/aegis-linux/target/release/examples/cis_witness'
OP = f'{S}/opmodel/exports/final_step12000/artifacts'
rc = sorted(glob.glob(f'{R}/labs/logs/safe/SAFE-01/h2_receipts/*.TXT'))
print('receipts on disk:', len(rc))
rng = random.Random(31337); pick = rng.sample(rc, 24)
env = dict(os.environ, OMP_NUM_THREADS='1', AEGIS_THREADS='1')
def work(p):
    grp = os.path.basename(p).split('__')[0]
    model = f'{S}/safe01/h2/{grp}/MODEL.SAF' if grp != 'orig_00' else f'{OP}/MODEL.SAF'
    out = []
    for fl in ([], ['--strict']):
        r = subprocess.run(['nice', '-n', '5', NEW, 'verify'] + fl + [model, f'{OP}/EMBED.BIN', f'{OP}/VOCAB.BIN', p], capture_output=True, env=env, timeout=300)
        o = r.stdout.decode('utf-8', 'replace')
        out.append((r.returncode, bool(re.search(r'^VERIFY PASS', o, re.M))))
    return os.path.basename(p), out
with ThreadPoolExecutor(2) as ex: res = list(ex.map(work, pick))
print('sampled', len(res), '; default PASS', sum(1 for _, o in res if o[0] == (0, True)), '; strict PASS', sum(1 for _, o in res if o[1] == (0, True)))
print('groups:', collections.Counter(n.split('__')[0][:3] for n, _ in res))
print('non-pass:', [(n, o) for n, o in res if o[0] != (0, True) or o[1] != (0, True)])
