"""VERIFY-2 side check: does `cis_witness verify` terminate on a receipt with a very long prompt? (Rule A: only 'finished within the harness limit or not' is recorded, no durations.)"""
import os, subprocess, re, sys
R = '/home/user/Ranger3143'; S = '/tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad'
NEW = '/home/user/aefinity-ai/alice-aegis/aegis-linux/target/release/examples/cis_witness'; OLD = f'{S}/harden/cis_witness.old'
OP = f'{S}/opmodel/exports/final_step12000/artifacts'; art = [f'{OP}/MODEL.SAF', f'{OP}/EMBED.BIN', f'{OP}/VOCAB.BIN']
g = open(f'{R}/labs/logs/opmodel/final_step12000/qemu_calc/RECEIPT.TXT', 'rb').read().split(b'\n')
LIMIT = 60
env = dict(os.environ, OMP_NUM_THREADS='1', AEGIS_THREADS='1')
os.makedirs(f'{S}/verify2/dos', exist_ok=True)
for fill, label in ((b'A', 'repeated letter'), (b'ab', 'alternating pair'), (b' ', 'spaces')):
    for n in (2000, 8000, 32000, 128000):
        data = (fill * n)[:n]
        rec = b'\n'.join((b'prompt-hex ' + data.hex().encode()) if l.startswith(b'prompt-hex ') else l for l in g)
        p = f'{S}/verify2/dos/r_{label.replace(" ", "_")}_{n}.txt'; open(p, 'wb').write(rec)
        row = []
        for name, b, fl in (('old', OLD, []), ('new-default', NEW, []), ('new-strict', NEW, ['--strict'])):
            try:
                r = subprocess.run(['nice', '-n', '5', b, 'verify'] + fl + art + [p], capture_output=True, env=env, timeout=LIMIT)
                out = r.stdout.decode('utf-8', 'replace').strip().split('\n')[-1][:60]
                row.append(f'{name}: finished exit={r.returncode} "{out}"')
            except subprocess.TimeoutExpired:
                row.append(f'{name}: NOT finished within {LIMIT} s limit')
        print(f'{label:16s} prompt bytes={n:6d} | ' + ' | '.join(row), flush=True)
