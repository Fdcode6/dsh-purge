"""Local-only Windows desktop setup; payloads are read from the adjacent bundle."""
import argparse, csv, datetime, hashlib, io, json, os, pathlib, shutil, subprocess, sys, tarfile, zipfile

BUNDLE = pathlib.Path(__file__).resolve().parent.parent

def run(args, **kw):
    print('RUN:', ' '.join(map(str,args)), flush=True)
    result=subprocess.run(list(map(str,args)),stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,**kw)
    print(result.stdout.decode('utf-8',errors='replace'),flush=True)
    result.check_returncode()
    return result

def unpack(archive, destination):
    destination = pathlib.Path(destination).resolve()
    destination.mkdir(parents=True,exist_ok=True)
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as z:
            for m in z.infolist():
                if not (destination/m.filename).resolve().is_relative_to(destination):
                    raise RuntimeError('Archive path escapes destination')
            z.extractall(destination)
    else:
        with tarfile.open(archive) as t:
            t.extractall(destination,filter='data')

def verify_manifest():
    manifest=json.loads((BUNDLE/'manifest.json').read_text(encoding='utf-8-sig'))
    for item in manifest['files']:
        f=(BUNDLE/item['path']).resolve()
        if not f.is_relative_to(BUNDLE) or not f.is_file():
            raise RuntimeError('Missing/invalid bundle path: '+item['path'])
        with f.open('rb') as stream:
            digest=hashlib.file_digest(stream,'sha256').hexdigest()
        if digest!=item['sha256']:
            raise RuntimeError('SHA256 mismatch: '+item['path'])
    print('Bundle integrity: PASS',flush=True)

def backup(file):
    if file.exists():
        dest=pathlib.Path(str(file)+'.backup-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        shutil.copy2(file,dest)
        print('BACKUP:',dest,flush=True)

def tools_at(root, nmap_override=None):
    tk=root/'redteam/toolkit'
    nmap_candidates=[pathlib.Path(nmap_override)] if nmap_override else [
        pathlib.Path(os.environ.get('ProgramFiles(x86)','C:/Program Files (x86)'))/'Nmap/nmap.exe',
        pathlib.Path(os.environ.get('ProgramFiles','C:/Program Files'))/'Nmap/nmap.exe']
    nmap=next((x for x in nmap_candidates if x.is_file()),nmap_candidates[0])
    paths={k:tk/k/(k+'.exe') for k in ['nuclei','httpx','dnsx','subfinder','ffuf','fscan','gogo','suo5','chisel','masscan','ksubdomain']}
    paths.update(nmap=nmap,frpc=tk/'frp/frp_0.71.1_windows_amd64/frpc.exe',frps=tk/'frp/frp_0.71.1_windows_amd64/frps.exe',impacket=tk/'impacket-venv/Scripts')
    return paths

def check_tools(root, nmap_override=None):
    paths=tools_at(root,nmap_override)
    flags={'nuclei':['-version'],'httpx':['-version'],'dnsx':['-version'],'subfinder':['-version'],
           'ffuf':['-V'],'fscan':['--help'],'gogo':['-h'],'suo5':['--help'],'chisel':['--version'],
           'masscan':['--selftest'],'ksubdomain':['--help'],'frpc':['--version'],'frps':['--version'],'nmap':['--version']}
    results={}
    for name,p in paths.items():
        try:
            args=[p,*flags[name]] if name!='impacket' else [p/'python.exe','-c','from impacket import version; import impacket.smbconnection; print(version.BANNER)']
            proc=subprocess.run(list(map(str,args)),capture_output=True,timeout=30)
            output=(proc.stdout+proc.stderr).decode('utf-8',errors='replace')
            # The pinned bundle was tested with these flags returning 0.
            ok=proc.returncode==0 and bool(output.strip())
            results[name]={'path':str(p),'ok':ok,'exit':proc.returncode,'output':output[:1800]}
        except Exception as exc:
            results[name]={'path':str(p),'ok':False,'error':str(exc)}
        print('CHECK:',name,'PASS' if results[name]['ok'] else 'FAIL',flush=True)
    return paths,results

def configure(root,cache,nmap_override=None):
    if sys.version_info[:2]!=(3,13) or sys.maxsize<2**32:
        raise RuntimeError('Use Python 3.13 x64; the offline wheel set targets CPython 3.13 / Windows x64.')
    running=subprocess.check_output(['tasklist','/FI','IMAGENAME eq DeepSeek Harness.exe','/FO','CSV','/NH'],text=True,errors='replace')
    if 'DeepSeek Harness.exe' in running:
        raise RuntimeError('Exit DeepSeek Harness completely (including tray) before configuring.')
    profile=root/'profiles/desktop'
    package=profile/'package.json'
    data=json.loads(package.read_text(encoding='utf-8-sig'))
    if data.get('name')!='dsh-profile-desktop':raise RuntimeError('Not the desktop profile')
    plugin=root/'plugins/dsh-purge'
    if not plugin.exists():
        unpack(BUNDLE/'sources/dsh-purge-1.1.71-original.tar.gz',plugin)
    installed=json.loads((plugin/'package.json').read_text(encoding='utf-8-sig'))
    if installed.get('name')!='dsh-purge' or installed.get('version')!='1.1.71':
        raise RuntimeError('Existing plugin is not 1.1.71; inspect and back up before changing versions.')
    backup(package)
    backup(profile/'pnpm-lock.yaml')
    data.setdefault('dependencies',{})['dsh-purge']='file:../../plugins/dsh-purge'
    bundles=data.setdefault('dsh',{}).setdefault('profile',{}).setdefault('bundles',[])
    if 'dsh-purge' not in bundles:bundles.append('dsh-purge')
    package.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    unpack(BUNDLE/'runtime/node-v26.8.1-win-x64.zip',cache/'node')
    unpack(BUNDLE/'runtime/pnpm-11.25.0.tgz',cache/'pnpm')
    node=cache/'node/node-v26.8.1-win-x64/node.exe'
    pnpm=cache/'pnpm/package/bin/pnpm.cjs'
    env=os.environ.copy()
    env['PATH']=str(node.parent)+os.pathsep+env.get('PATH','')
    run([node,pnpm,'install','--offline','--ignore-scripts','--config.auto-install-peers=false','--config.node-linker=hoisted'],cwd=profile,env=env)
    run([sys.executable,BUNDLE/'scripts/fix_cwd.py',root])
    run([sys.executable,BUNDLE/'scripts/fix_preset.py',root])
    run([sys.executable,BUNDLE/'scripts/lock_updates.py',root])
    for p in [plugin,profile/'node_modules/dsh-purge']:
        run([node,'--check',p/'lib/redteam/index.js'])
        run([node,'--check',p/'lib/redteam/preset-compat.js'])
    for p in [plugin,profile/'node_modules/dsh-purge']:run([node,'--check',p/'lib/identity.js'])
    tk=root/'redteam/toolkit'
    manifest=json.loads((BUNDLE/'portable-tools.json').read_text())
    for name,item in manifest.items():
        dest=tk/name
        if dest.exists():
            print('KEEP EXISTING:',dest,flush=True)
            continue
        asset=BUNDLE/'tools'/item['file']
        if asset.suffix=='.zip':unpack(asset,dest)
        else:
            dest.mkdir(parents=True,exist_ok=True)
            shutil.copy2(asset,dest/(name+'.exe'))
    if not (tk/'nuclei-templates').exists():unpack(BUNDLE/'tools/nuclei-templates-snapshot.zip',tk/'nuclei-templates')
    venv=tk/'impacket-venv'
    if not (venv/'Scripts/python.exe').exists():run([sys.executable,'-m','venv',venv])
    py=venv/'Scripts/python.exe'
    run([py,'-m','pip','install','--no-index','--disable-pip-version-check','--progress-bar','off','--find-links',BUNDLE/'python-wheels','-r',BUNDLE/'python-wheels/requirements-lock.txt'])
    run([py,'-m','pip','check'])
    paths,checks=check_tools(root,nmap_override)
    report=root/'redteam/local-install-checks.json'
    report.write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
    failures=[k for k,v in checks.items() if not v['ok']]
    if failures:raise RuntimeError('Tools not verified: '+', '.join(failures)+'. Read '+str(report))
    run([paths['nuclei'],'-validate','-t',tk/'nuclei-templates/http/technologies/4D-detect.yaml','-disable-update-check'])
    config=root/'redteam/config.json'
    backup(config)
    config_script=cache/'save-config.mjs'
    config_script.write_text('''import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const root=process.argv[2]; process.env.DSH_HOME=root;
const {savePlatformConfig,platformSummary}=await import(pathToFileURL(path.join(root,'plugins/dsh-purge/lib/redteam/platform-config.js')).href);
const tools=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
const rt=path.join(root,'redteam');
savePlatformConfig({platform:'windows',toolkitDir:path.join(rt,'toolkit'),nucleiTemplatesDir:path.join(rt,'toolkit/nuclei-templates'),tools,binDirs:[...new Set(Object.entries(tools).map(([k,p])=>k==='impacket'?p:path.dirname(p)))],envAdaptConfigured:true,envAdaptSkip:false},rt);
const s=platformSummary(rt);
console.log(JSON.stringify({ready:s.adapt.ready,found:s.tools.found,total:s.tools.total,missing:s.tools.missing,skipped:s.adapt.skipped},null,2));
if(s.tools.found!==15||s.tools.missing!==0||!s.adapt.ready) process.exitCode=1;
''',encoding='utf-8')
    pathfile=cache/'tool-paths.json'
    pathfile.write_text(json.dumps({k:str(p) for k,p in paths.items()}),encoding='utf-8')
    run([node,config_script,root,pathfile])
    print('LOCAL CONFIGURATION COMPLETE. Restart Harness, verify a normal conversation, and inspect the environment page. FOFA/VPS/additional skills are not configured.',flush=True)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('mode',choices=['configure','verify'])
    parser.add_argument('--dsh-root',required=True)
    parser.add_argument('--nmap')
    opts=parser.parse_args()
    verify_manifest()
    root=pathlib.Path(opts.dsh_root).resolve()
    cache=pathlib.Path(os.environ['LOCALAPPDATA'])/'DshPurgeSetup/1.1.71'
    cache.mkdir(parents=True,exist_ok=True)
    if opts.mode=='configure':configure(root,cache,opts.nmap)
    else:
        _,checks=check_tools(root,opts.nmap)
        if not all(v['ok'] for v in checks.values()):raise RuntimeError('One or more checks failed')
        print('All 15 executable checks passed. This does not prove every skill is configured.')

if __name__=='__main__':
    try:main()
    except Exception as error:
        print('FAILED:',error,file=sys.stderr,flush=True)
        sys.exit(1)
