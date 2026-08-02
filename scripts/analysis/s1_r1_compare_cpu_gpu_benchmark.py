#!/usr/bin/env python3
"""Compare matching CPU/GPU benchmark rows and emit speedups."""
from __future__ import annotations
import argparse, json
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--cpu',required=True); ap.add_argument('--gpu',required=True); ap.add_argument('--output-json',required=True); ap.add_argument('--output-md',required=True); args=ap.parse_args()
    cpu=json.loads(Path(args.cpu).read_text(encoding='utf-8')); gpu=json.loads(Path(args.gpu).read_text(encoding='utf-8')); c={r['batch']:r for r in cpu['rows']}; rows=[]
    for g in gpu['rows']:
        b=g['batch']; row={'batch':b}
        for kind in ('forward','forward_autograd'):
            cm=c[b][kind]['median_ms']; gm=g[kind]['median_ms']; row[kind]={'cpu_median_ms':cm,'gpu_median_ms':gm,'speedup_x':cm/gm if gm else None}
        rows.append(row)
    data={'cpu_torch':cpu.get('torch_version'),'gpu_torch':gpu.get('torch_version'),'gpu_device':gpu.get('device'),'rows':rows,'key_autograd_speedups':{str(r['batch']):r['forward_autograd']['speedup_x'] for r in rows}}
    Path(args.output_json).write_text(json.dumps(data,indent=2),encoding='utf-8')
    lines=['# CPU/GPU 工作空间模型对比','','仅比较同一网络、float32、batch、预热20次/正式100次的中位数；GPU 每次计时前后同步。','', '|batch|forward CPU ms|forward GPU ms|forward speedup|autograd CPU ms|autograd GPU ms|autograd speedup|','|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows: lines.append(f"|{r['batch']}|{r['forward']['cpu_median_ms']:.3f}|{r['forward']['gpu_median_ms']:.3f}|{r['forward']['speedup_x']:.2f}x|{r['forward_autograd']['cpu_median_ms']:.3f}|{r['forward_autograd']['gpu_median_ms']:.3f}|{r['forward_autograd']['speedup_x']:.2f}x|")
    Path(args.output_md).write_text('\n'.join(lines)+'\n',encoding='utf-8'); print(json.dumps(data,indent=2))
if __name__=='__main__': main()
