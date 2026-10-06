#!/bin/bash
# Machine fingerprint for every lab log (Rule A: name the machine; flag VMs).
echo "date_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "cpu_model: $(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2 | sed 's/^ //')"
echo "cpu_family_model_stepping: $(awk -F: '/^cpu family/{f=$2} /^model\t/{m=$2} /^stepping/{s=$2} END{print f","m","s}' /proc/cpuinfo | tr -d ' ')"
echo "logical_cpus: $(nproc)"
echo "hypervisor_flag: $(grep -m1 -c hypervisor /proc/cpuinfo)"
echo "isa_flags(relevant): $(grep -m1 '^flags' /proc/cpuinfo | grep -o -E '\b(avx|avx2|fma|avx512f|avx512bw|avx512vnni|avx_vnni|amx_tile|amx_int8)\b' | sort -u | tr '\n' ',' | sed 's/,$//')"
echo "mem_total_kb: $(grep MemTotal /proc/meminfo | awk '{print $2}')"
echo "os: $(uname -srmo)"
echo "env: $( [ "$(grep -m1 -c hypervisor /proc/cpuinfo)" = 1 ] && echo vm || echo iron ) (cloud container; NOT a performance ceiling; Rule A: ratios only)"
echo "rustc: $(rustc --version)"
echo "alice_aegis_head: $(git -C /home/user/aefinity-ai/alice-aegis rev-parse HEAD) (branch $(git -C /home/user/aefinity-ai/alice-aegis rev-parse --abbrev-ref HEAD))"
