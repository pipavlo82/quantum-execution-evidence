import argparse
import json
import sys
from . import checker

def verification_exit(out):
    # Evidence contradictions, link rejection and availability stay separate axes.
    if out['input_status']!='VALID': return 2
    if 'REFUTED' in (out['integrity'],out['request_binding'],out['deterministic_verification']): return 1
    link=out['native_link']
    if link['status']=='MALFORMED': return 5
    if link['status']=='REJECTED' or link.get('result',{}).get('valid') is False: return 4
    if link['status']!='EXECUTED' or link.get('result',{}).get('valid') is not True: return 3
    if out['deterministic_verification']=='CANNOT_ESTABLISH': return 3
    return 0

def main():
    parser=argparse.ArgumentParser(description='OFFLINE SYNTHETIC quantum evidence experiment')
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('demo'); sub.add_parser('mutation-check'); sub.add_parser('sources')
    sub.add_parser('rvr-demo'); sub.add_parser('rvr-mutation-check'); sub.add_parser('receiptos-demo'); sub.add_parser('tsei-demo'); sub.add_parser('quantum-transpile-demo'); sub.add_parser('provider-binding-demo'); sub.add_parser('ibm-runtime-demo')
    sub.add_parser('live-demo'); sub.add_parser('live-mutation-check')
    live_replay=sub.add_parser('live-replay'); live_replay.add_argument('artifact'); live_replay.add_argument('--claim')
    for name in ('verify','check'):
        p=sub.add_parser(name); p.add_argument('--request',required=True); p.add_argument('package')
    args=parser.parse_args()
    if args.command in ('live-demo','live-replay','live-mutation-check'):
        from .live_cli import dispatch
        out,code=dispatch(args)
    elif args.command=='demo':
        from .corpus import report, successful
        out=report(); code=0 if successful(out) else 1
    elif args.command=='mutation-check':
        from .mutations import run, successful
        out=run(); code=0 if successful(out) else 1
    elif args.command=='sources':
        from .sources import validate, successful
        out=validate(); code=0 if successful(out) else 1
    elif args.command=='rvr-demo':
        from .rvr_native import run_gate
        out=run_gate(); code=0 if out.get('gate')=='RVR_QEV_NATIVE_PROFILE_PASS' else 1
    elif args.command=='rvr-mutation-check':
        from .rvr_mutations import run, successful
        out=run(); code=0 if successful(out) else 1
    elif args.command=='receiptos-demo':
        from .receiptos_native import run_gate
        out=run_gate(); code=0 if out.get('gate')=='RECEIPTOS_QEV_NATIVE_CAPSULE_PASS' else 1
    elif args.command=='tsei-demo':
        from .tsei_native import run_gate
        out=run_gate(); code=0 if out.get('gate')=='TSEI_QEV_NATIVE_PRESERVATION_PASS' else 1
    elif args.command=='quantum-transpile-demo':
        from .quantum_transpile_native import run_gate
        out=run_gate(); code=0 if out.get('gate')=='QEV_QUANTUM_LAYOUT_TRANSPILATION_BOUNDARY_PASS' else 1
    elif args.command=='provider-binding-demo':
        from .provider_binding_native import run_gate
        out=run_gate(); code=0 if out.get('gate')=='QEV_PROVIDER_EXECUTION_BINDING_V0_PASS' else 1
    elif args.command=='ibm-runtime-demo':
        from .ibm_runtime_native import run_gate
        out=run_gate(); code=0 if out.get('gate')=='QEV_IBM_RUNTIME_ADAPTER_V0_PASS' else 1
    else:
        try: out=checker.verify(checker.read_input(args.request),checker.read_input(args.package))
        except (checker.InputError,OSError) as exc:
            out=checker.empty_result(); out['input_status']='INVALID'; out['reasons']=[str(exc)]
        code=verification_exit(out)
    sys.stdout.buffer.write((json.dumps(out,sort_keys=True,indent=2,ensure_ascii=True)+'\n').encode())
    return code

if __name__=='__main__': sys.exit(main())
