"""Report which original trials qualify, then score the three eligible people with both fixed models."""
import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

from qualified import execute

HERE = Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('recordings',type=Path,help='Directory holding the eight original assessment MAT files with their source receipts')
    parser.add_argument('--shared',type=Path,default=HERE.parent/'neurotranslate-0.0',help='Extracted NeuroTranslate 0.0 directory containing predict.py and movement-weights.npz')
    parser.add_argument('--out',type=Path,required=True,help='New directory for two descriptive summaries and the label check')
    args=parser.parse_args()
    shared=args.shared.resolve()
    files=(shared/'predict.py',shared/'movement-weights.npz',shared/'back_rotation/model.json')
    if not all(p.is_file() for p in files):
        parser.error('Extract the NeuroTranslate 0.0 model ZIP and pass its directory with --shared.')
    out=args.out.resolve()
    if out.exists():parser.error('Choose a new output directory.')
    out.parent.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(dir=out.parent) as tmp:
        stage=Path(tmp)/'result'
        spec,shared_result=execute(args.recordings.resolve(),HERE,shared/'back_rotation',files[1],files[2],stage)
        assert spec['assessment_status']==shared_result['assessment_status']=='incomplete'
        stage.rename(out)
    print(f'Four-person tests incomplete. Wrote descriptive results for three people to {out}.')

if __name__=='__main__':
    main()
