import datetime, pathlib, shutil, sys
root = pathlib.Path(sys.argv[1]).resolve()
payload = pathlib.Path(__file__).resolve().parent.parent / 'patches/preset-compat.js'
for package in [root / 'plugins/dsh-purge', root / 'profiles/desktop/node_modules/dsh-purge']:
    index = package / 'lib/redteam/index.js'
    text = index.read_text(encoding='utf-8-sig')
    old_import = "import { readPresetDefinition } from './preset-composition.js'"
    new_import = "import { registerCompatiblePresets } from './preset-compat.js'"
    old_call = 'releaseDeclared = await registry.register(definition)'
    new_call = 'releaseDeclared = await registerCompatiblePresets(registry, definition)'
    if old_import not in text or (old_call not in text and new_call not in text):
        raise RuntimeError('Unknown preset loader; inspect before patching: ' + str(index))
    updated = text if new_import in text else text.replace(old_import, old_import + '\n' + new_import)
    updated = updated.replace(old_call, new_call)
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    if updated != text:
        shutil.copy2(index, str(index) + '.backup-' + stamp)
        index.write_text(updated, encoding='utf-8')
    target = package / 'lib/redteam/preset-compat.js'
    data = payload.read_bytes()
    if not target.exists() or target.read_bytes() != data:
        if target.exists(): shutil.copy2(target, str(target) + '.backup-' + stamp)
        target.write_bytes(data)
    print('Preset compatibility patch ready:', package)
print('Restart Harness, then inspect redteam/preset-declare.json; file patching alone is not runtime validation.')
