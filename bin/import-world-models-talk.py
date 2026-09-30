#!/usr/bin/env python3
"""Import the browser deck as a standalone page with separately served media.

Usage: python3 bin/import-world-models-talk.py /path/to/world-models
The source directory must contain deck.template.html, world-models.html and
assets/. Speaker notes come from the built offline deck. No Jekyll front matter
is added, so the presentation retains its own layout and is copied verbatim.
"""

import json
import re
import shutil
import sys
from pathlib import Path

SAVE_FUNCTION = r'''async function save(){
 const button=$('#saveBtn');button.disabled=true;toast('Preparing the offline presentation…');
 try{
  const clone=document.documentElement.cloneNode(true);
  clone.querySelector('body').classList.remove('editing','fullscreen','motion-paused');
  clone.querySelectorAll('[contenteditable]').forEach(el=>el.removeAttribute('contenteditable'));
  clone.querySelector('#thumbGrid').replaceChildren();
  ['#overview','#notes','#help'].forEach(selector=>clone.querySelector(selector).hidden=true);
  clone.querySelector('#toast').classList.remove('show');clone.querySelector('#saveBtn').disabled=false;
  const assets=new Map();
  clone.querySelectorAll('[src],[poster]').forEach(el=>['src','poster'].forEach(attribute=>{
   const path=el.getAttribute(attribute);
   if(path&&path.startsWith('assets/')){
    if(!assets.has(path))assets.set(path,[]);
    assets.get(path).push([el,attribute]);
   }
  }));
  await Promise.all([...assets].map(async([path,targets])=>{
   const response=await fetch(new URL(path,location.href));
   if(!response.ok)throw new Error(`Could not download ${path}`);
   const blob=await response.blob();
   const data=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=()=>reject(reader.error);reader.readAsDataURL(blob)});
   targets.forEach(([el,attribute])=>el.setAttribute(attribute,data));
  }));
  const url=URL.createObjectURL(new Blob(['<!doctype html>\n'+clone.outerHTML],{type:'text/html'}));
  const a=document.createElement('a');a.href=url;a.download='world-models-for-fluid-dynamics.html';a.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);toast('Saved an offline presentation with your current text.');
 }catch(error){console.error(error);toast('Download failed. Please check your connection and try again.');}
 finally{button.disabled=false;}
}'''


def main() -> None:
    """Copy referenced assets and adapt the deck's offline download control."""
    source = Path(sys.argv[1]).resolve()
    target = Path(__file__).resolve().parents[1] / 'talks/world-models-fluid-dynamics'
    template = (source / 'deck.template.html').read_text()
    standalone = (source / 'world-models.html').read_text()
    note_match = re.search(r'const deckNotes = (.*?);\nconst \$', standalone, re.S)
    assert note_match, 'Built deck is missing speaker notes'
    notes = json.loads(note_match.group(1))
    assert len(notes) == template.count('<section class="slide'), 'Notes are stale'
    html = template.replace('__NOTES__', note_match.group(1))
    html, count = re.subn(r'function save\(\)\{.*?\}\n(?=\$\(\x27#prev)', lambda _: SAVE_FUNCTION + '\n', html, flags=re.S)
    assert count == 1, 'Download function was not found'
    html = html.replace("const storageKey='physical-world-deck-v1-edits'", "const storageKey='world-models-fluid-dynamics-v1-edits'")
    # Only the active video needs to load; play() initiates its request.
    html = re.sub(r'(<video\b[^>]*?) preload="[^"]*"', r'\1', html)
    html = re.sub(r'<video\b', '<video preload="none"', html)
    html = html.replace('title="Download an editable, standalone HTML copy"', 'title="Download an offline copy including all videos and current text edits"')
    media = set(re.findall(r'(?:src|poster)="(assets/[^"]+)"', html))
    target.mkdir(parents=True, exist_ok=True)
    for name in sorted(media):
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / name, destination)
    (target / 'index.html').write_text(html)
    print(f'{len(notes)} slides, {len(media)} media files; HTML {len(html.encode()) / 1000:.0f} kB')


if __name__ == '__main__':
    main()
