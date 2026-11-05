"""Exact, versioned PR review-base policy. Grants no deployment authority."""
import json
import os
import re
import sys

LEGACY_BASE='c08de12dbee5bcb64efe91641438efcdf9e96796'
STACK_BASE='7f23e746a3a52163c3065975ff02d6a7ae790129'
STACK_HEAD='mission3/runtime-dashboard-20261031'
STACK_REF='mission1/composed-terminan-20261031'


def select_policy(event,head_ref,base_ref,base_sha):
    if any(type(v) is not str for v in (event,head_ref,base_ref,base_sha)):
        raise ValueError('REVIEW_BASE_DRIFT')
    if event=='push' and not any((head_ref,base_ref,base_sha)):
        policy='NON_PR_NO_BASE'
    elif event=='pull_request' and head_ref and base_ref and re.fullmatch('[a-f0-9]{40}',base_sha):
        if head_ref==STACK_HEAD:
            if (base_ref,base_sha)!=(STACK_REF,STACK_BASE):raise ValueError('REVIEW_BASE_DRIFT')
            policy='MISSION3_STACK_EXACT_7F'
        elif base_sha==LEGACY_BASE:policy='LEGACY_EXACT_C08'
        else:raise ValueError('REVIEW_BASE_DRIFT')
    else:raise ValueError('REVIEW_BASE_DRIFT')
    return dict(schema='terminan.review-base-policy.v1',policy=policy,head_ref=head_ref,base_ref=base_ref,base_sha=base_sha,physical_authority='NOT_GRANTED')


def main():
    try:
        result=select_policy(os.environ.get('GITHUB_EVENT_NAME',''),os.environ.get('GITHUB_HEAD_REF',''),os.environ.get('GITHUB_BASE_REF',''),os.environ.get('TERMINAN_REVIEW_BASE_SHA',''))
    except ValueError:
        print('REVIEW_BASE_DRIFT',file=sys.stderr);return 1
    print(json.dumps(result,sort_keys=True));return 0


if __name__=='__main__':raise SystemExit(main())
