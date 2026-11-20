"""Write group summaries for distribution, retaining support for singleton channels."""
import argparse
import json
from pathlib import Path


def omit_singletons(node):
    if isinstance(node,list):
        for v in node: omit_singletons(v)
    if not isinstance(node,dict): return
    if 'scores' in node and 'channel_counts' in node:
        if node.get('people')==1:
            node['scores']={}
        else:
            for name,count in node['channel_counts'].items():
                if count['people']<2:
                    node['scores'].pop('mae '+name,None)
                    node['scores'].pop('bias '+name,None)
    for v in node.values(): omit_singletons(v)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('input',type=Path)
    p.add_argument('output',type=Path)
    args=p.parse_args()
    data=json.loads(args.input.read_text())
    omit_singletons(data)
    data['reporting']='Channel means and signed errors are omitted wherever fewer than two participants contributed. The available muscle remains in the frozen primary group score. Counts give its support.'
    args.output.write_text(json.dumps(data,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n')
